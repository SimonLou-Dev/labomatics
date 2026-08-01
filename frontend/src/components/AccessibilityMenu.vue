<template>
  <div class="relative">
    <button
      @click="isOpen = !isOpen"
      class="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
      :aria-expanded="isOpen"
      aria-label="Paramètres d'accessibilité"
      title="Accessibilité"
    >
      <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8c1.657 0 3-1.343 3-3s-1.343-3-3-3-3 1.343-3 3 1.343 3 3 3zm0 0h.01M9 19h6m0 0v1m0-1a9 9 0 01-18 0 9 9 0 0118 0zm-5-5a1 1 0 11-2 0 1 1 0 012 0zm7 0a1 1 0 11-2 0 1 1 0 012 0z" />
      </svg>
    </button>

    <!-- Dropdown menu -->
    <div
      v-if="isOpen"
      class="absolute right-0 mt-2 w-64 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg shadow-lg z-50"
    >
      <div class="p-4 space-y-4">
        <div class="font-semibold text-gray-900 dark:text-gray-50">Accessibilité</div>

        <!-- Dyslexia mode -->
        <label class="flex items-center gap-3 cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-700 p-2 rounded transition-colors">
          <input
            v-model="a11y.dyslexiaMode"
            type="checkbox"
            class="w-4 h-4 rounded border-gray-300 text-primary-500 cursor-pointer"
          />
          <div class="flex-1">
            <div class="text-sm font-medium text-gray-900 dark:text-gray-50">Mode dyslexie</div>
            <div class="text-xs text-gray-500">Police OpenDyslexic</div>
          </div>
        </label>

        <!-- High contrast -->
        <label class="flex items-center gap-3 cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-700 p-2 rounded transition-colors">
          <input
            v-model="a11y.highContrast"
            type="checkbox"
            class="w-4 h-4 rounded border-gray-300 text-primary-500 cursor-pointer"
          />
          <div class="flex-1">
            <div class="text-sm font-medium text-gray-900 dark:text-gray-50">Contraste élevé</div>
            <div class="text-xs text-gray-500">Couleurs plus contrastées</div>
          </div>
        </label>

        <!-- Large text -->
        <label class="flex items-center gap-3 cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-700 p-2 rounded transition-colors">
          <input
            v-model="a11y.largeText"
            type="checkbox"
            class="w-4 h-4 rounded border-gray-300 text-primary-500 cursor-pointer"
          />
          <div class="flex-1">
            <div class="text-sm font-medium text-gray-900 dark:text-gray-50">Texte plus grand</div>
            <div class="text-xs text-gray-500">Augmente la taille du texte</div>
          </div>
        </label>
      </div>
    </div>

    <!-- Backdrop to close menu -->
    <div v-if="isOpen" class="fixed inset-0 z-40" @click="isOpen = false"></div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useA11yStore } from '@/stores/a11y'

const isOpen = ref(false)
const a11y = useA11yStore()
</script>
