<template>
  <div class="bg-white min-h-screen p-6">
    <div class="flex justify-between items-center mb-6">
      <h2 class="text-2xl font-bold text-slate-800">Today's Picks</h2>
      <span class="text-sm text-slate-500">Tokyo 📍</span>
    </div>

    <div v-if="isLoading" class="text-center py-12 text-slate-500">
      Loading 3D Products...
    </div>

    <div v-else class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
      <div
        v-for="item in productsList"
        :key="item.id || item.title"
        class="bg-white border border-slate-200 rounded-lg overflow-hidden hover:shadow-md transition"
      >
        <div class="w-full h-72 bg-slate-50 border-b border-slate-200 relative overflow-hidden">
          
          <!-- 常规 .glb 模型 -->
          <model-viewer
            v-if="!isSplatModel(item)"
            :src="item.modelUrl || item.model_url"
            camera-controls
            auto-rotate
            ar
            shadow-intensity="1"
            environment-image="neutral"
            style="width: 100%; height: 100%; background-color: #f7f7f7"
          ></model-viewer>

          <!-- 本地原生 3DGS 高清 .ply 渲染器 -->
          <SplatViewer
            v-else
            :src="item.modelUrl || item.model_url"
          />

          <span 
            v-if="isSplatModel(item)" 
            class="absolute top-2 left-2 bg-red-600 text-white text-[10px] font-bold px-2 py-0.5 rounded shadow z-10"
          >
            3DGS AI Reconstructed
          </span>
        </div>

        <div class="p-3">
          <div class="flex justify-between items-start mb-1">
            <h3 class="text-base font-semibold text-slate-800">
              {{ item.title }}
            </h3>
            <span class="text-slate-800 font-bold text-sm"
              >¥{{ item.price }}</span
            >
          </div>
          <p class="text-slate-500 text-xs mb-2 line-clamp-1">
            {{ item.description }}
          </p>

          <div class="flex justify-between items-center">
            <span class="text-xs text-slate-500 flex items-center gap-1">
              <i class="pi pi-map-marker text-[#BE0000]"></i>
              {{ item.location }}
            </span>
            <button
              class="bg-white hover:bg-red-50 text-xs text-[#BE0000] px-2 py-1.5 rounded-md border border-[#BE0000]"
            >
              Details / AR
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import SplatViewer from '../components/SplatViewer.vue'

const productsList = ref([])
const isLoading = ref(true)

const mockProducts = [
  {
    id: 'mock-1',
    title: "Game Toy",
    price: 2000,
    description: "Brand New, unopened, and in perfect condition.",
    location: "Dorm A - 302",
    modelUrl: "/models/toy.glb",
  },
  {
    id: 'mock-2',
    title: "Starbucks Cup",
    price: 500,
    description: "Used, but in good condition.",
    location: "On Campus",
    modelUrl: "/models/Starbucks_Cup.glb",
  },
  {
    id: 'mock-3',
    title: "Sony Headphones",
    price: 10000,
    description: "Noise-canceling feature.",
    location: "Sangenjyaya Station",
    modelUrl: "/models/sony-headphone.glb",
  },
    {
    id: 'mock-4',
    title: "Sony Headphones",
    price: 10000,
    description: "Noise-canceling feature.",
    location: "Sangenjyaya Station",
    modelUrl: "/models/18d1e31e.ply",
  },
]

const isSplatModel = (item) => {
  const url = item.modelUrl || item.model_url || ''
  return url.endsWith('.ply') || url.endsWith('.splat')
}

const fetchProducts = async () => {
  try {
    const res = await fetch('http://localhost:8000/api/products')
    if (res.ok) {
      const data = await res.json()
      if (data && data.length > 0) {
        productsList.value = [...data.reverse(), ...mockProducts]
      } else {
        productsList.value = mockProducts
      }
    } else {
      productsList.value = mockProducts
    }
  } catch (err) {
    console.error('API Error, fallback to mock data:', err)
    productsList.value = mockProducts
  } finally {
    isLoading.value = false
  }
}

onMounted(() => {
  fetchProducts()
})
</script>