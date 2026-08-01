<template>
  <div class="min-h-screen bg-surface-color text-text-color">
    <router-view />
  </div>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useTheme } from '@/composables/useTheme'
import { onMounted } from 'vue'

const router = useRouter()
const auth = useAuthStore()
const { initTheme, initDyslexia } = useTheme()

onMounted(async () => {
  initTheme()
  initDyslexia()

  // Récupérer l'utilisateur depuis les cookies (via /me endpoint)
  // Les tokens sont dans les cookies HTTPOnly, pas besoin de les gérer côté frontend
  if (!auth.user) {
    try {
      await auth.fetchMe()
      // Si on a un utilisateur et on est sur /login, rediriger vers /
      if (auth.user && router.currentRoute.value.path === '/login') {
        await router.push('/')
      }
    } catch {
      // Si /me échoue, on est pas connecté
      if (router.currentRoute.value.path !== '/login') {
        await router.push('/login')
      }
    }
  }
})
</script>
