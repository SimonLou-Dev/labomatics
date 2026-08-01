<template>
  <div class="min-h-screen flex items-center justify-center bg-surface-900 dark:bg-surface-900 px-4">
    <div class="w-full max-w-md">
      <Card class="shadow-lg">
        <template #content>
          <div class="text-center space-y-8">
            <img src="@/assets/logo-large.svg" alt="Labomatics" class="h-20 mx-auto" />

            <div class="pt-4">
              <Button
                label="Connexion Keycloak"
                class="w-full mb-4 [&_.p-button-label]:font-medium"
                :style="{ backgroundColor: 'rgb(var(--primary-600))', borderColor: 'rgb(var(--primary-600))' }"
                @click="handleLogin"
                :loading="loading"
                :icon="`pi pi-sign-in`"
              />
            </div>

            <Message v-if="error" severity="error" :text="error" class="w-full" />
          </div>
        </template>
      </Card>

    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useAuthStore } from '@/stores/auth'
import Button from 'primevue/button'
import Card from 'primevue/card'
import Message from 'primevue/message'

const auth = useAuthStore()
const loading = ref(false)
const error = ref<string | null>(null)

const handleLogin = async () => {
  loading.value = true
  error.value = null
  try {
    await auth.login()
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Login failed'
    loading.value = false
  }
}
</script>
