import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { getMe } from '@/api/auth'
import { env } from '@/config/env'
import type { MeDTO } from '@/api'

export const useAuthStore = defineStore('auth', () => {
  const user = ref<MeDTO | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)

  // isAuthenticated = on a un utilisateur (tokens dans les cookies HTTPOnly)
  const isAuthenticated = computed(() => !!user.value)
  const hasRole = (role: string) => user.value?.roles.includes(role) ?? false

  const fetchMe = () => {
    loading.value = true
    error.value = null

    return getMe()
      .then((data) => {
        user.value = data
        error.value = null
      })
      .catch((err) => {
        error.value = err instanceof Error ? err.message : 'Failed to fetch user'
        user.value = null
        throw err
      })
      .finally(() => {
        loading.value = false
      })
  }

  const login = () => {
    const redirect = window.location.origin + window.location.pathname + '#/'
    const loginUrl = `${env.apiUrl}/v1/auth/login?redirect=${encodeURIComponent(redirect)}`
    window.location.href = loginUrl
  }

  const logoutUser = () => {
    // Le backend révoque le refresh token, supprime les cookies et redirige
    // le navigateur vers Keycloak (même principe que login()) : navigation
    // directe, pas un appel AJAX, pour que la redirection soit suivie par le navigateur.
    user.value = null
    window.location.href = `${env.apiUrl}/v1/auth/logout`
  }

  return {
    user,
    loading,
    error,
    isAuthenticated,
    hasRole,
    fetchMe,
    login,
    logoutUser,
  }
})
