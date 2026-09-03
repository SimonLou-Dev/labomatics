<template>
  <Dialog
    v-model:visible="visible"
    header="Créer un lab"
    modal
    :style="{ width: '100vw', maxWidth: '600px' }"
    @update:visible="emitClose"
  >
    <!-- Loading state -->
    <div v-if="loading" class="flex justify-center items-center h-40">
      <ProgressSpinner />
    </div>

    <!-- Success state -->
    <div v-else-if="successMessage" class="bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg p-4">
      <div class="flex items-start gap-3">
        <i class="pi pi-check-circle text-green-600 dark:text-green-400 text-2xl mt-1 flex-shrink-0"></i>
        <div>
          <h3 class="font-semibold text-green-900 dark:text-green-100 mb-2">Lab créé avec succès!</h3>
          <p class="text-green-700 dark:text-green-200 text-sm mb-2">
            {{ successMessage }}
          </p>
          <div class="bg-green-100 dark:bg-green-900/50 rounded px-3 py-2 font-mono text-sm text-green-800 dark:text-green-200">
            {{ jobId }}
          </div>
          <p class="text-green-600 dark:text-green-300 text-xs mt-3">
            Un email vous sera envoyé lorsque votre lab sera prêt.
          </p>
        </div>
      </div>
    </div>

    <!-- Form -->
    <div v-else class="space-y-4">
      <!-- Error alert -->
      <div v-if="error" class="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4">
        <div class="flex items-start gap-3">
          <i class="pi pi-exclamation-circle text-red-600 dark:text-red-400 text-lg mt-1 flex-shrink-0"></i>
          <div>
            <h3 class="font-semibold text-red-900 dark:text-red-100 mb-1">Erreur</h3>
            <p class="text-red-700 dark:text-red-200 text-sm">{{ error }}</p>
          </div>
        </div>
      </div>

      <!-- Cluster selection (only for teacher/admin) -->
      <div v-if="!isStudent">
        <label class="block text-sm font-medium mb-3">
          Cluster <span class="text-red-500">*</span>
        </label>
        <Dropdown
          v-model="selectedClusterId"
          :options="availableClusters"
          optionLabel="name"
          optionValue="id"
          placeholder="Sélectionner un cluster"
          :loading="loadingClusters"
          class="w-full"
          :showClear="false"
        />
        <p class="text-xs text-surface-500 dark:text-surface-400 mt-2">
          Sélectionnez le cluster où provisioner le lab
        </p>
      </div>

      <!-- Info message for students -->
      <div v-else class="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-3">
        <div class="flex items-start gap-2">
          <i class="pi pi-info-circle text-blue-600 dark:text-blue-400 text-lg mt-0.5 flex-shrink-0"></i>
          <p class="text-sm text-blue-700 dark:text-blue-200">
            Votre lab sera créé sur le cluster par défaut de votre promotion.
          </p>
        </div>
      </div>

      <!-- Description -->
      <div class="bg-surface-50 dark:bg-surface-900 border border-surface-200 dark:border-surface-700 rounded-lg p-3">
        <p class="text-sm text-surface-600 dark:text-surface-400">
          La création du lab provisionnera:
        </p>
        <ul class="text-sm text-surface-600 dark:text-surface-400 mt-2 space-y-1 ml-4">
          <li class="list-disc">Une VM OpenWRT pour le routage</li>
          <li class="list-disc">Les allocations réseau (IP WAN, tag VXLAN)</li>
          <li class="list-disc">L'accès SSH et web à votre infrastructure</li>
        </ul>
      </div>
    </div>

    <!-- Footer -->
    <template #footer>
      <Button
        v-if="!successMessage"
        label="Annuler"
        severity="secondary"
        @click="emitClose"
      />
      <Button
        v-if="!successMessage"
        label="Créer le lab"
        :loading="creating"
        :disabled="!isStudent && !selectedClusterId"
        @click="createLab"
      />
      <Button
        v-if="successMessage"
        label="Fermer"
        @click="emitClose"
      />
    </template>
  </Dialog>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useToast } from 'primevue/usetoast'
import {
  Dialog,
  Button,
  Dropdown,
  ProgressSpinner,
} from 'primevue'
import type { ClusterDTO } from '@/api/types'

interface Props {
  visible: boolean
  isStudent: boolean
  userCohortName?: string
}

const props = withDefaults(defineProps<Props>(), {
  visible: false,
  isStudent: false,
})

const emit = defineEmits<{
  'update:visible': [value: boolean]
}>()

const toast = useToast()

const selectedClusterId = ref<string | null>(null)
const availableClusters = ref<ClusterDTO[]>([])
const loadingClusters = ref(false)
const creating = ref(false)
const loading = ref(false)
const error = ref<string | null>(null)
const successMessage = ref<string | null>(null)
const jobId = ref<string | null>(null)

const visible = computed({
  get: () => props.visible,
  set: (value) => emit('update:visible', value),
})

function emitClose() {
  visible.value = false
  // Reset state when closing
  if (!successMessage.value) {
    error.value = null
    selectedClusterId.value = null
  } else {
    // If success, reset everything
    successMessage.value = null
    jobId.value = null
  }
}

async function fetchClusters() {
  loadingClusters.value = true
  try {
    // TODO: Import and call actual API
    // const response = await clustersApi.listClusters(1, 100)
    // availableClusters.value = response.items
    console.log('Fetch clusters from API')
  } catch (err) {
    error.value = 'Impossible de charger les clusters disponibles'
    toast.add({
      severity: 'error',
      summary: 'Erreur',
      detail: error.value,
      life: 3000,
    })
  } finally {
    loadingClusters.value = false
  }
}

async function createLab() {
  error.value = null

  if (!props.isStudent && !selectedClusterId.value) {
    error.value = 'Veuillez sélectionner un cluster'
    return
  }

  creating.value = true
  loading.value = true

  try {
    const clusterId = props.isStudent
      ? undefined // Will use default from backend
      : selectedClusterId.value

    // TODO: Call actual API
    // const response = await labsApi.createLab({
    //   cluster_id: clusterId,
    // })
    // jobId.value = response.job_id

    // Mock response for now
    const mockJobId = `job-${Date.now()}`
    jobId.value = mockJobId

    successMessage.value = `Lab creation started! JobID: ${mockJobId}. You'll receive an email when ready.`

    toast.add({
      severity: 'success',
      summary: 'Succès',
      detail: 'Création du lab lancée',
      life: 3000,
    })
  } catch (err) {
    const message = err instanceof Error ? err.message : 'Erreur inconnue'
    error.value = `Impossible de créer le lab: ${message}`
    toast.add({
      severity: 'error',
      summary: 'Erreur',
      detail: error.value,
      life: 3000,
    })
    console.error('Failed to create lab:', err)
  } finally {
    creating.value = false
    loading.value = false
  }
}

onMounted(() => {
  if (!props.isStudent) {
    fetchClusters()
  }
})
</script>
