<template>
  <div class="min-h-screen bg-surface-900 dark:bg-surface-50 p-6">
    <!-- Header -->
    <div class="mb-6">
      <Button
        label="Retour au tableau de bord"
        icon="pi pi-arrow-left"
        severity="secondary"
        @click="goToDashboard"
        class="mb-4"
      />
      <h1 v-if="labData?.student" class="text-3xl font-bold">
        Mon Lab — {{ labData.student.first_name }} {{ labData.student.last_name }} (WAN: {{ labData.wan_ip }})
      </h1>
    </div>

    <!-- Loading state -->
    <div v-if="loading" class="flex justify-center items-center h-96">
      <ProgressSpinner />
    </div>

    <!-- Error state -->
    <div v-else-if="error" class="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-6">
      <div class="flex items-start gap-4">
        <i class="pi pi-exclamation-circle text-red-600 dark:text-red-400 text-xl mt-1"></i>
        <div>
          <h3 class="font-semibold text-red-900 dark:text-red-100">Erreur</h3>
          <p class="text-red-700 dark:text-red-200 text-sm mt-1">{{ error }}</p>
        </div>
      </div>
    </div>

    <!-- No Lab State -->
    <div v-if="!labData?.student" class="flex flex-col items-center justify-center h-96 gap-4">
      <i class="pi pi-inbox text-6xl text-surface-400"></i>
      <h2 class="text-2xl font-semibold">Pas de lab créé</h2>
      <p class="text-surface-600 dark:text-surface-400 text-center max-w-md">
        Vous n'avez pas encore créé de lab. Cliquez sur le bouton ci-dessous pour en demander la création.
      </p>
      <Button
        label="Créer mon lab"
        icon="pi pi-plus"
        size="large"
        class="bg-primary-lab-600 hover:bg-primary-lab-700 text-white"
        @click="requestLabCreation"
        :loading="creatingLab"
      />
    </div>

    <!-- Content -->
    <div v-if="labData?.student">
      <!-- Student Info Card -->
      <Card class="mb-6">
        <template #title>Informations Étudiant</template>
        <template #content>
          <div class="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div>
            <div class="text-sm text-surface-500 dark:text-surface-400 mb-1">Étudiant</div>
            <div class="text-lg font-semibold">{{ labData.student.first_name }} {{ labData.student.last_name }}</div>
            <div class="text-sm text-surface-400">{{ labData.student.login }}</div>
          </div>
          <div>
            <div class="text-sm text-surface-500 dark:text-surface-400 mb-1">Email</div>
            <div class="text-sm font-mono">{{ labData.student.email }}</div>
          </div>
          <div>
            <div class="text-sm text-surface-500 dark:text-surface-400 mb-1">Promotion</div>
            <div class="text-sm">{{ labData.student.cohort_name }}</div>
          </div>
          <div>
            <div class="text-sm text-surface-500 dark:text-surface-400 mb-1">Date de création</div>
            <div class="text-sm">{{ formatDate(labData.student.created_at) }}</div>
          </div>
        </div>
        </template>
      </Card>

      <!-- Allocations Network -->
      <Card class="mb-6">
        <template #title>Allocations Réseau</template>
        <template #content>
          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div class="border border-surface-200 dark:border-surface-700 rounded-lg p-4">
            <div class="text-sm text-surface-500 dark:text-surface-400 mb-2">Adresse IP WAN</div>
            <div class="flex items-center justify-between">
              <span class="text-lg font-mono font-bold">
                {{ labData.wan_ip || 'Non allouée' }}
              </span>
              <i
                v-if="labData.wan_ip"
                class="pi pi-check-circle"
                style="color: var(--green-500)"
              ></i>
              <i
                v-else
                class="pi pi-circle text-surface-400"
              ></i>
            </div>
          </div>

          <div class="border border-surface-200 dark:border-surface-700 rounded-lg p-4">
            <div class="text-sm text-surface-500 dark:text-surface-400 mb-2">Tag VXLAN</div>
            <div class="flex items-center justify-between">
              <span class="text-lg font-mono font-bold">
                {{ labData.vxlan_tag !== null ? labData.vxlan_tag : 'Non alloué' }}
              </span>
              <i
                v-if="labData.vxlan_tag !== null"
                class="pi pi-check-circle"
                style="color: var(--green-500)"
              ></i>
              <i
                v-else
                class="pi pi-circle text-surface-400"
              ></i>
            </div>
          </div>
        </div>
        </template>
      </Card>

      <!-- VMs Table -->
      <Card class="mb-6">
        <template #title>Machines Virtuelles Provisionnées</template>
        <template #content>
          <DataTable
          :value="labData.vms"
          dataKey="id"
          :loading="loading"
        >
          <template #empty>Aucune VM provisionnée</template>
          <Column field="name" header="Nom" style="width: 20%">
            <template #body="{ data }">
              <span class="font-semibold">{{ data.name }}</span>
            </template>
          </Column>
          <Column field="cluster_name" header="Cluster" style="width: 15%">
            <template #body="{ data }">
              <span class="text-sm">{{ data.cluster_name }}</span>
            </template>
          </Column>
          <Column field="state" header="État" style="width: 12%">
            <template #body="{ data }">
              <Tag
                :value="data.state"
                :severity="getStateSeverity(data.state)"
              />
            </template>
          </Column>
          <Column field="cores" header="CPUs" style="width: 10%">
            <template #body="{ data }">
              <span class="text-sm">{{ data.cores }}</span>
            </template>
          </Column>
          <Column field="memory" header="Mémoire" style="width: 15%">
            <template #body="{ data }">
              <span class="text-sm font-mono">{{ formatMemory(data.memory) }}</span>
            </template>
          </Column>
          <Column field="disk" header="Disque" style="width: 13%">
            <template #body="{ data }">
              <span class="text-sm font-mono">{{ data.disk }} GB</span>
            </template>
          </Column>
          <Column field="created_at" header="Créée" style="width: 15%">
            <template #body="{ data }">
              <span class="text-sm">{{ formatDate(data.created_at) }}</span>
            </template>
          </Column>
        </DataTable>
        </template>
      </Card>

      <!-- TODO Section -->
      <Card class="bg-amber-900/20 border-2 border-amber-700">
        <template #title>À compléter</template>
        <template #content>
          <ul class="space-y-2 text-sm text-amber-800 dark:text-amber-200">
              <li class="flex items-start gap-2">
                <i class="pi pi-times-circle text-amber-500 text-xs mt-1 flex-shrink-0"></i>
                <span>[ ] Affichage des VMs provisionnées depuis le backend</span>
              </li>
              <li class="flex items-start gap-2">
                <i class="pi pi-times-circle text-amber-500 text-xs mt-1 flex-shrink-0"></i>
                <span>[ ] Affichage des allocations réseau détaillées</span>
              </li>
              <li class="flex items-start gap-2">
                <i class="pi pi-times-circle text-amber-500 text-xs mt-1 flex-shrink-0"></i>
                <span>[ ] Accès OpenWRT (lien))</span>
              </li>
              <li class="flex items-start gap-2">
                <i class="pi pi-times-circle text-amber-500 text-xs mt-1 flex-shrink-0"></i>
                <span>[ ] Bouton de création VM (futur)</span>
              </li>
              <li class="flex items-start gap-2">
                <i class="pi pi-times-circle text-amber-500 text-xs mt-1 flex-shrink-0"></i>
                <span>[ ] Logs de provisioning</span>
              </li>
          </ul>
          <p class="text-xs text-amber-700 dark:text-amber-300 mt-3 italic">
            Cette page affiche le détail du lab étudiant. Les données seront complétées progressivement.
          </p>
        </template>
      </Card>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useToast } from 'primevue/usetoast'
import {
  Card,
  DataTable,
  Column,
  Button,
  ProgressSpinner,
  Tag,
} from 'primevue'
import type { LabDataDTO } from '@/api/types'
import * as studentsApi from '@/api/students'
import * as labsApi from '@/api/labs'

const router = useRouter()
const route = useRoute()
const toast = useToast()

const labData = ref<LabDataDTO | null>(null)
const loading = ref(false)
const creatingLab = ref(false)
const error = ref<string | null>(null)

function formatDate(dateString: string): string {
  try {
    const date = new Date(dateString)
    return date.toLocaleDateString('fr-FR', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  } catch {
    return dateString
  }
}

function formatMemory(mb: number): string {
  if (mb >= 1024) {
    return `${(mb / 1024).toFixed(1)} GB`
  }
  return `${mb} MB`
}

function getStateSeverity(state: string): string {
  const lower = state.toLowerCase()
  if (lower === 'running') return 'success'
  if (lower === 'stopped') return 'secondary'
  if (lower === 'error') return 'danger'
  return 'info'
}

async function fetchLabData() {
  loading.value = true
  error.value = null
  try {
    const userId = route.params.userId as string | undefined

    if (userId) {
      // Admin viewing student's lab
      labData.value = await studentsApi.getLabData(userId)
    } else {
      // Student viewing their own lab
      labData.value = await studentsApi.getLabDataForMe()
    }
  } catch (err) {
    const message = err instanceof Error ? err.message : 'Erreur inconnue'
    error.value = `Impossible de charger les données du lab: ${message}`
    toast.add({
      severity: 'error',
      summary: 'Erreur',
      detail: error.value,
      life: 3000,
    })
    console.error('Failed to fetch lab data:', err)
  } finally {
    loading.value = false
  }
}

async function requestLabCreation() {
  creatingLab.value = true
  error.value = null
  try {
    await labsApi.createLab()
    toast.add({
      severity: 'success',
      summary: 'Succès',
      detail: 'Création du lab en cours. Vous recevrez un email quand ce sera prêt.',
      life: 5000,
    })
    // Refresh data after a short delay
    setTimeout(() => {
      fetchLabData()
    }, 2000)
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
    creatingLab.value = false
  }
}

function goToDashboard() {
  router.push('/')
}

onMounted(() => {
  fetchLabData()
})
</script>
