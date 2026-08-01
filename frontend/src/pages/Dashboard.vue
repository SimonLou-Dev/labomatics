<template>
  <div class="min-h-screen bg-white">
    <div class="max-w-7xl mx-auto px-6 py-12">
      <h1 class="text-4xl font-bold text-gray-900 mb-2">Palette de couleurs</h1>
      <p class="text-gray-600 mb-12">Design system Labomatics</p>

      <!-- Primary Colors -->
      <div class="mb-12">
        <h2 class="text-2xl font-bold text-gray-900 mb-6">Primaire (Orange)</h2>
        <div class="grid grid-cols-2 md:grid-cols-6 gap-4">
          <div v-for="shade in primaryShades" :key="shade" class="text-center">
            <div :style="{ backgroundColor: `rgb(var(--primary-${shade}))` }" class="h-24 rounded-lg mb-2 border border-gray-300" />
            <p class="text-xs font-medium text-gray-600">primary-{{ shade }}</p>
            <p class="text-xs text-gray-500">rgb(var(--primary-{{ shade }}))</p>
          </div>
        </div>
      </div>

      <!-- Secondary Colors (Steel) -->
      <div class="mb-12">
        <h2 class="text-2xl font-bold text-gray-900 mb-6">Secondaire (Steel)</h2>
        <div class="grid grid-cols-2 md:grid-cols-6 gap-4">
          <div v-for="shade in surfaceShades" :key="shade" class="text-center">
            <div :style="{ backgroundColor: `rgb(var(--surface-${shade}))` }" class="h-24 rounded-lg mb-2 border border-gray-300" />
            <p class="text-xs font-medium text-gray-600">surface-{{ shade }}</p>
            <p class="text-xs text-gray-500">rgb(var(--surface-{{ shade }}))</p>
          </div>
        </div>
      </div>

      <!-- Surface Colors Light -->
      <div class="mb-12">
        <h2 class="text-2xl font-bold text-gray-900 mb-6">Surface (Light Mode)</h2>
        <div class="grid grid-cols-2 md:grid-cols-6 gap-4">
          <div v-for="shade in surfaceShades" :key="shade" class="text-center">
            <div :style="{ backgroundColor: `rgb(var(--surface-${shade}))` }" class="h-24 rounded-lg mb-2 border border-gray-300" />
            <p class="text-xs font-medium text-gray-600">surface-{{ shade }}</p>
            <p class="text-xs text-gray-500">rgb(var(--surface-{{ shade }}))</p>
          </div>
        </div>
      </div>

      <!-- Surface Colors Dark -->
      <div class="mb-12">
        <h2 class="text-2xl font-bold text-gray-900 mb-6">Surface (Dark Mode)</h2>
        <div class="grid grid-cols-2 md:grid-cols-6 gap-4">
          <div v-for="shade in surfaceShades" :key="shade" class="text-center">
            <div :style="{ backgroundColor: `rgb(var(--surface-${shade}))` }" class="h-24 rounded-lg mb-2 border border-gray-300" />
            <p class="text-xs font-medium text-gray-600">surface-{{ shade }}</p>
            <p class="text-xs text-gray-500">rgb(var(--surface-{{ shade }}))</p>
          </div>
        </div>
      </div>

      <!-- Semantic Colors -->
      <div class="mb-12">
        <h2 class="text-2xl font-bold text-gray-900 mb-6">Sémantiques</h2>
        <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div v-for="(color, name) in semanticColors" :key="name" class="text-center">
            <div :style="{ backgroundColor: color }" class="h-24 rounded-lg mb-2 border border-gray-300" />
            <p class="text-xs font-medium text-gray-600 capitalize">{{ name }}</p>
            <p class="text-xs text-gray-500">{{ color }}</p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
const primaryShades = ['50', '100', '200', '300', '400', '500', '600', '700', '800', '900', '950']
const surfaceShades = ['0', '50', '100', '150', '200', '300', '400', '500', '600', '700', '800', '900', '950']

const semanticColors = {
  success: '#10B981',
  warning: '#F59E0B',
  error: '#EF4444',
  info: '#3B82F6',
}
</script>
