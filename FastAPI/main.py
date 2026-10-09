import sys
import os
import shutil
from pathlib import Path

os.environ["PYTORCH_CUDA_ALLOC_CONF"] = "expandable_segments:True"

SAM2_DIR = Path.home() / "sam2"
if str(SAM2_DIR) not in sys.path:
    sys.path.insert(0, str(SAM2_DIR))

from fastapi import FastAPI, HTTPException, Depends, UploadFile, File
from fastapi.responses import RedirectResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Field, Session, SQLModel, create_engine, select
from typing import Optional
import httpx
from jose import jwt
from datetime import datetime, timedelta
from dotenv import load_dotenv

import asyncio
import uuid
import glob
import cv2
import numpy as np
import torch
import trimesh

load_dotenv(".env")

# 数据模型
class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(unique=True, index=True)
    name: str
    avatar_url: str = ""
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())

class Product(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str
    price: int
    description: str
    location: str
    model_url: str
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())

# 数据库配置
engine = create_engine("sqlite:///visionmarket.db", echo=False)

def create_db():
    SQLModel.metadata.create_all(engine)

app = FastAPI()
create_db()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
JWT_SECRET = os.getenv("JWT_SECRET")
REDIRECT_URI = "http://localhost:8000/auth/google/callback"

jobs = {}
BASE_DIR = Path.home() / "code/script"
SAM2_CKPT = str(SAM2_DIR / "checkpoints/sam2.1_hiera_small.pt")
SAM2_CFG = "configs/sam2.1/sam2.1_hiera_s.yaml"
GSPLAT_TRAINER = str(Path.home() / "code/gsplat/examples/simple_trainer.py")

# WSL2 路径挂载
VUE_PUBLIC_MODELS_DIR = Path("/mnt/c/Users/70957/Desktop/Capstone-Lateset/vuejs/vue-project/public/models")
VUE_PUBLIC_MODELS_DIR.mkdir(parents=True, exist_ok=True)

def create_jwt(user: User) -> str:
    payload = {
        "sub": user.email,
        "name": user.name,
        "avatar": user.avatar_url,
        "user_id": user.id,
        "exp": datetime.utcnow() + timedelta(days=7)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")

# 认证接口
@app.get("/auth/google")
def google_login():
    url = (
        "https://accounts.google.com/o/oauth2/v2/auth"
        f"?client_id={GOOGLE_CLIENT_ID}"
        f"&redirect_uri={REDIRECT_URI}"
        "&response_type=code"
        "&scope=openid email profile"
    )
    return RedirectResponse(url)

@app.get("/auth/google/callback")
async def google_callback(code: str):
    async with httpx.AsyncClient() as client:
        token_res = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code": code,
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "redirect_uri": REDIRECT_URI,
                "grant_type": "authorization_code",
            }
        )
        access_token = token_res.json().get("access_token")
        user_res = await client.get(
            "https://www.googleapis.com/oauth2/v2/userinfo",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        info = user_res.json()

    with Session(engine) as session:
        user = session.exec(select(User).where(User.email == info["email"])).first()
        if not user:
            user = User(email=info["email"], name=info["name"], avatar_url=info.get("picture", ""))
            session.add(user)
            session.commit()
            session.refresh(user)

    token = create_jwt(user)
    return RedirectResponse(f"http://localhost:5173/auth/success?token={token}")

@app.get("/auth/me")
def get_me(token: str):
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
    except:
        raise HTTPException(status_code=401, detail="Invalid token")

# 商品与用户管理
@app.get("/api/products")
def get_products():
    with Session(engine) as session:
        return session.exec(select(Product)).all()

@app.get("/admin/users")
def list_users():
    with Session(engine) as session:
        return session.exec(select(User)).all()

@app.delete("/admin/users/{user_id}")
def delete_user(user_id: int):
    with Session(engine) as session:
        user = session.get(User, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        session.delete(user)
        session.commit()
        return {"deleted": user_id}

# 3DGS 重建管线
@app.get("/status/{job_id}")
def get_status(job_id: str):
    return jobs.get(job_id, {"status": "not found"})

@app.get("/download/{job_id}")
def download_ply(job_id: str):
    project_dir = BASE_DIR / f"project_{job_id}"
    ply_path = project_dir / "output" / f"{job_id}.ply"
    if ply_path.exists():
        return FileResponse(ply_path, media_type="application/octet-stream", filename=f"{job_id}.ply")
    raise HTTPException(status_code=404, detail="PLY file not found")

@app.post("/upload")
async def upload_video(video: UploadFile = File(...)):
    job_id = str(uuid.uuid4())[:8]
    project_dir = BASE_DIR / f"project_{job_id}"
    project_dir.mkdir(parents=True, exist_ok=True)

    video_path = project_dir / "input.mp4"
    with open(video_path, "wb") as f:
        f.write(await video.read())

    jobs[job_id] = {"status": "queued", "ply": None}
    asyncio.create_task(run_pipeline(job_id, project_dir, video_path))

    return {"job_id": job_id}

async def run_pipeline(job_id: str, project_dir: Path, video_path: Path):
    try:
        output_dir = project_dir / "output"
        images_dir = output_dir / "images"
        masks_dir = output_dir / "masks"
        images_dir.mkdir(parents=True, exist_ok=True)
        masks_dir.mkdir(parents=True, exist_ok=True)

        output_dir_str = str(output_dir)
        images_dir_str = str(images_dir)
        masks_dir_str = str(masks_dir)
        video_path_str = str(video_path)
        ply_path = output_dir / f"{job_id}.ply"

        # Step 1: 抽帧
        jobs[job_id]["status"] = "Step 1/4: Extracting frames"
        proc = await asyncio.create_subprocess_exec(
            "ffmpeg", "-y", "-i", video_path_str,
            "-vf", "fps=2,scale=w='min(1080,iw)':h=-1",
            str(images_dir / "%04d.jpg"),
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL
        )
        await proc.wait()
        if proc.returncode != 0:
            raise RuntimeError("ffmpeg failed")

        # Step 1.5: SAM2 抠图
        jobs[job_id]["status"] = "Step 1.5/4: AI background segmentation (SAM2)"
        await asyncio.to_thread(sync_sam2_segmentation, images_dir_str, masks_dir_str)

        # Step 2: COLMAP 重建
        jobs[job_id]["status"] = "Step 2/4: Running COLMAP"
        proc = await asyncio.create_subprocess_exec(
            "colmap", "automatic_reconstructor",
            "--workspace_path", output_dir_str,
            "--image_path", images_dir_str,
            "--mask_path", masks_dir_str
        )
        await proc.wait()
        if proc.returncode != 0:
            raise RuntimeError("COLMAP failed")

        # Step 3: 3DGS 训练
        jobs[job_id]["status"] = "Step 3/4: Training 3DGS"
        proc = await asyncio.create_subprocess_exec(
            "python", GSPLAT_TRAINER,
            "default",
            "--data_dir", output_dir_str,
            "--result_dir", f"{output_dir_str}/results",
            "--data_factor", "1",
            "--disable_viewer",
        )
        await proc.wait()
        if proc.returncode != 0:
            raise RuntimeError("gsplat failed")

        # Step 4: 导出 PLY 并转化为前端能渲染的 GLB
        # Step 4: 导出带有 Three.js 标准 RGB 颜色通道的 PLY 资产
        jobs[job_id]["status"] = "Step 4/4: Exporting Standard PLY"

        ckpt_files = glob.glob(
            f"{output_dir_str}/results/ckpts/ckpt_*_rank0.pt"
        )
        if not ckpt_files:
          ckpt_files = glob.glob(
              f"{output_dir_str}/results/*/ckpts/ckpt_*_rank0.pt"
          )
        if not ckpt_files:
          raise FileNotFoundError("No checkpoint found")

        ckpt_path = sorted(
            ckpt_files, key=lambda x: int(x.split("ckpt_")[1].split("_")[0])
        )[-1]

        splats = torch.load(ckpt_path, map_location="cpu")["splats"]
        means = splats["means"].detach().cpu().numpy().astype(np.float32)
        f_dc = (
            splats["sh0"].detach().cpu().numpy().astype(np.float32)
            if "sh0" in splats
            else np.ones((len(means), 3), dtype=np.float32) * 0.5
        )
        if f_dc.ndim == 3:
          f_dc = f_dc.squeeze(1)
        if f_dc.shape[1] > 3:
          f_dc = f_dc[:, :3]

        # 1. 空间离群点过滤 (保留核心 92% 主体)
        center = np.median(means, axis=0)
        distances = np.linalg.norm(means - center, axis=1)
        dist_threshold = np.percentile(distances, 92)
        valid_mask = distances <= dist_threshold

        means = means[valid_mask]
        f_dc = f_dc[valid_mask]

        # 2. 0阶球谐 (sh0/f_dc) 直接在后端转成标准 uint8 RGB (0-255)
        SH_C0 = 0.28209479177387814
        rgb = np.clip((0.5 + SH_C0 * f_dc), 0.0, 1.0) * 255.0
        rgb_uint8 = rgb.astype(np.uint8)

        N = len(means)

        # 3. 写入带有标准 property uchar red/green/blue 头的 PLY
        with open(str(ply_path), "wb") as f:
          f.write(
              f"ply\nformat binary_little_endian 1.0\nelement vertex"
              f" {N}\n".encode()
          )
          f.write(b"property float x\nproperty float y\nproperty float z\n")
          f.write(
              b"property uchar red\nproperty uchar green\nproperty uchar"
              b" blue\n"
          )
          f.write(b"end_header\n")

          vertex_data = np.empty(
              N,
              dtype=[
                  ("x", "f4"),
                  ("y", "f4"),
                  ("z", "f4"),
                  ("red", "u1"),
                  ("green", "u1"),
                  ("blue", "u1"),
              ],
          )
          vertex_data["x"] = means[:, 0]
          vertex_data["y"] = means[:, 1]
          vertex_data["z"] = means[:, 2]
          vertex_data["red"] = rgb_uint8[:, 0]
          vertex_data["green"] = rgb_uint8[:, 1]
          vertex_data["blue"] = rgb_uint8[:, 2]

          f.write(vertex_data.tobytes())

        # 4. 同步导出到 Vue 的 public 目录 (改存为 .ply 路径)
        public_ply_filename = f"reconstructed_{job_id}.ply"
        target_public_path = VUE_PUBLIC_MODELS_DIR / public_ply_filename
        shutil.copy(str(ply_path), str(target_public_path))

        # 5. 写入数据库，生成前端卡片用的商品路径
        relative_model_url = f"/models/{public_ply_filename}"
        with Session(engine) as session:
          new_product = Product(
              title=f"3D Item #{job_id}",
              price=1500,
              description="Auto-generated 3D asset from video reconstruction.",
              location="Tokyo",
              model_url=relative_model_url,
          )
          session.add(new_product)
          session.commit()

        jobs[job_id]["status"] = "done"
        jobs[job_id]["ply"] = relative_model_url


    except Exception as e:
        import traceback
        traceback.print_exc()
        jobs[job_id]["status"] = f"failed: {str(e)}"

# SAM2 分割
def sync_sam2_segmentation(images_dir: str, masks_dir: str):
    from sam2.build_sam import build_sam2
    from sam2.automatic_mask_generator import SAM2AutomaticMaskGenerator

    device = "cuda" if torch.cuda.is_available() else "cpu"
    if not Path(SAM2_CKPT).exists():
        raise FileNotFoundError(f"Missing checkpoint: {SAM2_CKPT}")

    sam2 = build_sam2(SAM2_CFG, SAM2_CKPT, device=device)
    mask_generator = SAM2AutomaticMaskGenerator(
        sam2,
        points_per_side=16,
        points_per_batch=32,
        crop_n_layers=0
    )

    image_files = sorted(glob.glob(f"{images_dir}/*.jpg"))

    for img_path in image_files:
        image = cv2.imread(img_path)
        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        h, w = image.shape[:2]
        cx, cy = w // 2, h // 2

        with torch.no_grad():
            masks = mask_generator.generate(image_rgb)

        best_mask = None
        best_area = 0
        
        for m in masks:
            seg = m["segmentation"]
            if seg[cy, cx] and m["area"] > best_area:
                best_area = m["area"]
                best_mask = seg

        if best_mask is None and masks:
            valid_masks = [m for m in masks if m["area"] < (h * w * 0.7)]
            best_mask = (max(valid_masks, key=lambda x: x["area"])["segmentation"] 
                         if valid_masks else max(masks, key=lambda x: x["area"])["segmentation"])

        if best_mask is not None:
            mask_img = (best_mask * 255).astype(np.uint8)
            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
            mask_img = cv2.erode(mask_img, kernel, iterations=2)
        else:
            mask_img = np.ones((h, w), dtype=np.uint8) * 255

        out_name = Path(img_path).name
        cv2.imwrite(f"{masks_dir}/{out_name}", mask_img)

        if device == "cuda":
            torch.cuda.empty_cache()

    del mask_generator
    del sam2
    if device == "cuda":
        torch.cuda.empty_cache()