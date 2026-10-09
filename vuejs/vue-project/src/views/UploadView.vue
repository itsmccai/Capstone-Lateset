<script setup>
import { ref, computed, onUnmounted } from 'vue'

const selectedFile = ref(null)
const jobId = ref('')
const statusText = ref('')
const isProcessing = ref(false)
const plyDownloadUrl = ref('')
let timer = null

const handleFileChange = (e) => {
  if (e.target.files.length > 0) {
    selectedFile.value = e.target.files[0]
  }
}

const uploadVideo = async () => {
  if (!selectedFile.value) return alert('Please select a video file first!')

  const formData = new FormData()
  formData.append('video', selectedFile.value)

  isProcessing.value = true
  statusText.value = 'Uploading video...'
  plyDownloadUrl.value = ''

  try {
    const res = await fetch('http://localhost:8000/upload', {
      method: 'POST',
      body: formData
    })
    
    if (!res.ok) throw new Error('Failed to upload video')
    
    const data = await res.json()
    jobId.value = data.job_id
    startPolling()
  } catch (err) {
    statusText.value = 'Error: ' + err.message
    isProcessing.value = false
  }
}

const startPolling = () => {
  timer = setInterval(async () => {
    try {
      const res = await fetch(`http://localhost:8000/status/${jobId.value}`)
      const data = await res.json()

      statusText.value = data.status

      if (data.status === 'done') {
        clearInterval(timer)
        isProcessing.value = false
        plyDownloadUrl.value = `http://localhost:8000/download/${jobId.value}`
        statusText.value = '3D Reconstruction Completed Successfully!'
      } else if (data.status.startsWith('failed')) {
        clearInterval(timer)
        isProcessing.value = false
      }
    } catch (err) {
      console.error('Polling error:', err)
    }
  }, 2000)
}

// 映射不同步骤至 0-100% 进度
const progressPercentage = computed(() => {
  const status = statusText.value
  if (!status) return 0
  if (status.includes('Uploading')) return 10
  if (status.includes('Step 1/4')) return 25
  if (status.includes('Step 1.5/4')) return 40
  if (status.includes('Step 2/4')) return 60
  if (status.includes('Step 3/4')) return 85
  if (status.includes('Step 4/4')) return 95
  if (status === '3D Reconstruction Completed Successfully!' || status === 'done') return 100
  return 0
})

onUnmounted(() => {
  if (timer) clearInterval(timer)
})
</script>

<template>
  <div class="reconstruction-container">
    <div class="card">
      <h2 class="title">3DGS Product Reconstruction System</h2>
      <p class="subtitle">Upload item video to generate Gaussian Splatting 3D assets</p>
      
      <div class="file-input-wrapper">
        <input 
          type="file" 
          accept="video/*" 
          @change="handleFileChange" 
          :disabled="isProcessing" 
          id="video-upload"
        />
        <label for="video-upload" class="file-label">
          <span v-if="selectedFile">{{ selectedFile.name }}</span>
          <span v-else>📁 Click to select or drop video file</span>
        </label>
      </div>

      <button 
        class="submit-btn" 
        @click="uploadVideo" 
        :disabled="isProcessing || !selectedFile"
      >
        <span v-if="isProcessing">Processing Pipeline...</span>
        <span v-else>Start 3D Reconstruction</span>
      </button>

      <div v-if="isProcessing || progressPercentage === 100" class="progress-section">
        <div class="progress-header">
          <span class="status-label">{{ statusText }}</span>
          <span class="percentage-label">{{ progressPercentage }}%</span>
        </div>
        <div class="progress-bar-bg">
          <div 
            class="progress-bar-fill" 
            :style="{ width: progressPercentage + '%' }"
            :class="{ 'completed': progressPercentage === 100 }"
          ></div>
        </div>
      </div>

      <div v-if="plyDownloadUrl" class="result-section">
        <a :href="plyDownloadUrl" download class="download-btn">
          ⬇️ Download 3D Asset (.ply)
        </a>
      </div>
    </div>
  </div>
</template>

<style scoped>
.reconstruction-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 80vh;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
}

.card {
  background: #ffffff;
  padding: 2.5rem;
  border-radius: 16px;
  box-shadow: 0 10px 25px rgba(0, 0, 0, 0.08);
  width: 100%;
  max-width: 500px;
  text-align: center;
}

.title {
  margin: 0 0 0.5rem 0;
  color: #1a1a1a;
  font-size: 1.5rem;
  font-weight: 700;
}

.subtitle {
  margin: 0 0 2rem 0;
  color: #666666;
  font-size: 0.9rem;
}

.file-input-wrapper {
  margin-bottom: 1.5rem;
}

.file-input-wrapper input[type="file"] {
  display: none;
}

.file-label {
  display: block;
  padding: 1.2rem;
  border: 2px dashed #e0e0e0;
  border-radius: 10px;
  background: #fafafa;
  color: #555555;
  cursor: pointer;
  transition: all 0.2s ease;
  font-size: 0.95rem;
}

.file-label:hover {
  border-color: #BE0000;
  background: #fff5f5;
}

.submit-btn {
  width: 100%;
  padding: 0.9rem;
  border: none;
  border-radius: 8px;
  background: #BE0000;
  color: white;
  font-size: 1rem;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.2s ease;
}

.submit-btn:hover:not(:disabled) {
  background: #9e0000;
}

.submit-btn:disabled {
  background: #e58888;
  cursor: not-allowed;
}

.progress-section {
  margin-top: 2rem;
  text-align: left;
}

.progress-header {
  display: flex;
  justify-content: space-between;
  margin-bottom: 0.5rem;
  font-size: 0.85rem;
  color: #4b5563;
  font-weight: 500;
}

.progress-bar-bg {
  width: 100%;
  height: 10px;
  background-color: #e5e7eb;
  border-radius: 5px;
  overflow: hidden;
}

.progress-bar-fill {
  height: 100%;
  background-color: #BE0000;
  transition: width 0.4s ease;
  border-radius: 5px;
}

.progress-bar-fill.completed {
  background-color: #10b981;
}

.result-section {
  margin-top: 1.5rem;
}

.download-btn {
  display: inline-block;
  width: 100%;
  box-sizing: border-box;
  padding: 0.9rem;
  background: #10b981;
  color: white;
  border-radius: 8px;
  text-decoration: none;
  font-weight: 600;
  transition: background 0.2s ease;
}

.download-btn:hover {
  background: #059669;
}
</style>