<script setup>
import { onMounted } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()

onMounted(() => {
  const params = new URLSearchParams(window.location.search)
  const token = params.get('token')
  if (token) {
    localStorage.setItem('token', token)
  }
  router.push('/')
})
</script>

<template>
  <div class="flex items-center justify-center min-h-screen">
    <p class="text-slate-500">Logging you in...</p>
  </div>
</template>