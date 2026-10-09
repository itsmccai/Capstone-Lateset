<script setup>
import { ref, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'

const user = ref(null)
const route = useRoute()

const fetchUser = async () => {
  const token = localStorage.getItem('token')
  if (token) {
    try {
      const res = await fetch(`http://localhost:8000/auth/me?token=${token}`)
      if (res.ok) {
        user.value = await res.json()
      } else {
        localStorage.removeItem('token')
        user.value = null
      }
    } catch {
      user.value = null
    }
  } else {
    user.value = null
  }
}

// 页面首次加载
onMounted(fetchUser)

// 每次路由变化重新检查
watch(() => route.path, fetchUser)

const login = () => {
  window.location.href = 'http://localhost:8000/auth/google'
}

const logout = () => {
  localStorage.removeItem('token')
  user.value = null
}
</script>

<template>
  <nav class="bg-[#BE0000] text-white border-b border-red-900 px-6 py-4 flex flex-col md:flex-row items-center justify-between gap-4">
    <router-link to="/" class="text-xl font-bold text-white flex items-center gap-2">
      <i class="pi pi-box"></i> VisionMarket
    </router-link>

    <div class="relative w-full md:w-96">
      <span class="absolute inset-y-0 left-0 flex items-center pl-3 text-red-200">
        <i class="pi pi-search"></i>
      </span>
      <input 
        type="text" 
        placeholder="Search here..." 
        class="w-full bg-[#9A0000] border border-red-800 rounded-lg pl-10 pr-4 py-2 text-sm focus:outline-none focus:border-white text-white placeholder-red-300"
      />
    </div>

    <div class="flex items-center gap-6">
      <router-link to="/" class="text-sm font-medium hover:text-red-200 transition flex items-center gap-1">
        <i class="pi pi-home"></i> Browse 
      </router-link>
      <router-link to="/upload" class="bg-white hover:bg-red-100 text-[#BE0000] text-sm px-4 py-2 rounded-lg font-medium transition flex items-center gap-1">
        <i class="pi pi-upload"></i> Sell your product
      </router-link>

      <!-- 已登录 -->
      <div v-if="user" class="flex items-center gap-2">
        <img :src="user.avatar" class="w-8 h-8 rounded-full border-2 border-white" />
        <span class="text-sm text-white">{{ user.name }}</span>
        <button @click="logout" class="text-xs text-red-200 hover:text-white transition">
          Logout
        </button>
      </div>

      <!-- 未登录 -->
      <button v-else @click="login" class="flex items-center gap-2 bg-white hover:bg-red-50 text-[#BE0000] text-sm px-4 py-2 rounded-lg font-medium transition">
        <img src="https://www.google.com/favicon.ico" class="w-4 h-4" />
        Login
      </button>
    </div>
  </nav>
</template>