<script setup>
import Navbar from './components/Navbar.vue';
</script>

<template>
  <div class="min-h-screen bg-white font-sans text-slate-800">
    <Navbar />

    <main class="max-w-7xl mx-auto p-6">
      <router-view />
    </main>
  </div>
</template>