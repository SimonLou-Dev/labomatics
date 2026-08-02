<template>
  <div class="min-h-screen bg-surface-900 dark:bg-surface-50 flex items-center justify-center p-6">
    <div class="text-center max-w-md">
      <div class="mb-6">
        <i class="pi pi-shield-exclamation text-6xl text-red-500"></i>
      </div>
      <h1 class="text-4xl font-bold mb-2">403</h1>
      <h2 class="text-2xl font-semibold mb-4">Accès Refusé</h2>
      <p class="text-surface-600 dark:text-surface-400 mb-6">
        Vous n'avez pas les permissions nécessaires pour accéder à cette ressource.
      </p>
      <div class="flex gap-3 justify-center">
        <Button
          label="Retour à l'accueil"
          icon="pi pi-arrow-left"
          @click="goHome"
        />
        <Button
          label="Contacter l'admin"
          icon="pi pi-envelope"
          severity="secondary"
          @click="contactAdmin"
        />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router'
import { Button } from 'primevue'

const router = useRouter()

function goHome() {
  router.push('/')
}

function contactAdmin() {
  window.location.href = 'mailto:admin@example.com'
}
</script>
