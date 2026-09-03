<template>
  <div class="space-y-6">
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

    <!-- No lab created -->
    <div v-else-if="!labData" class="bg-amber-50 dark:bg-amber-900/20 border-2 border-amber-200 dark:border-amber-800 rounded-lg p-6">
      <div class="flex items-start gap-4">
        <i class="pi pi-info-circle text-amber-600 dark:text-amber-400 text-2xl mt-1 flex-shrink-0"></i>
        <div class="flex-1">
          <h3 class="font-bold text-amber-900 dark:text-amber-100 mb-2">Laboratoire non créé</h3>
          <p class="text-amber-800 dark:text-amber-200 text-sm mb-4">
            Vous n'avez pas encore de lab. Créez-en un pour commencer.
          </p>
          <Button
            label="Créer un lab"
            icon="pi pi-plus"
            @click="$emit('create-lab')"
          />
        </div>
      </div>
    </div>

    <!-- Lab info cards -->
    <div v-else>
      <!-- Header Card with basic info -->
      <Card class="mb-6 p-6 bg-gradient-to-r from-primary-50 to-primary-100 dark:from-primary-900/20 dark:to-primary-900/40 border border-primary-200 dark:border-primary-800">
        <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
          <!-- Lab Status -->
          <div>
            <div class="text-xs font-semibold text-primary-600 dark:text-primary-400 uppercase tracking-wide mb-2">
              Statut Lab
            </div>
            <div class="flex items-center gap-3">
              <div
                class="w-3 h-3 rounded-full flex-shrink-0"
                :style="{ backgroundColor: getStatusColor(labData.status) }"
              ></div>
              <span class="text-lg font-bold">{{ formatStatus(labData.status) }}</span>
            </div>
          </div>

          <!-- Created Date -->
          <div>
            <div class="text-xs font-semibold text-primary-600 dark:text-primary-400 uppercase tracking-wide mb-2">
              Date de création
            </div>
            <span class="text-lg font-mono">{{ formatDate(labData.created_at) }}</span>
          </div>

          <!-- Cluster -->
          <div>
            <div class="text-xs font-semibold text-primary-600 dark:text-primary-400 uppercase tracking-wide mb-2">
              Cluster
            </div>
            <span class="text-lg font-bold">{{ labData.cluster_name || '—' }}</span>
          </div>
        </div>
      </Card>

      <!-- Network Allocations -->
      <Card class="mb-6 p-6">
        <h2 class="text-xl font-bold mb-4 flex items-center gap-2">
          <i class="pi pi-network text-primary-600"></i>
          Allocations Réseau
        </h2>
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <!-- WAN IP -->
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
              <i v-else class="pi pi-circle text-surface-400"></i>
            </div>
            <p class="text-xs text-surface-500 dark:text-surface-400 mt-2">
              Accessible depuis l'extérieur
            </p>
          </div>

          <!-- VXLAN Tag -->
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
              <i v-else class="pi pi-circle text-surface-400"></i>
            </div>
            <p class="text-xs text-surface-500 dark:text-surface-400 mt-2">
              Isolation réseau inter-labs
            </p>
          </div>

          <!-- Subnet -->
          <div v-if="labData.subnet" class="border border-surface-200 dark:border-surface-700 rounded-lg p-4">
            <div class="text-sm text-surface-500 dark:text-surface-400 mb-2">Sous-réseau privé</div>
            <div class="flex items-center justify-between">
              <span class="text-lg font-mono font-bold">{{ labData.subnet }}</span>
              <i class="pi pi-check-circle" style="color: var(--green-500)"></i>
            </div>
            <p class="text-xs text-surface-500 dark:text-surface-400 mt-2">
              Réseau interne du lab
            </p>
          </div>

          <!-- VM Count -->
          <div class="border border-surface-200 dark:border-surface-700 rounded-lg p-4">
            <div class="text-sm text-surface-500 dark:text-surface-400 mb-2">Machines Virtuelles</div>
            <div class="flex items-center gap-3">
              <span class="text-2xl font-bold">{{ labData.vm_count || 0 }}</span>
              <i
                v-if="(labData.vm_count || 0) > 0"
                class="pi pi-check-circle text-green-500 text-xl"
              ></i>
              <i v-else class="pi pi-circle text-surface-400"></i>
            </div>
            <p class="text-xs text-surface-500 dark:text-surface-400 mt-2">
              VMs provisionnées
            </p>
          </div>
        </div>
      </Card>

      <!-- OpenWRT Access -->
      <Card v-if="labData.openwrt_url" class="mb-6 p-6 border-2 border-green-200 dark:border-green-800 bg-green-50 dark:bg-green-900/20">
        <div class="flex items-start gap-4">
          <i class="pi pi-router text-green-600 dark:text-green-400 text-2xl mt-1 flex-shrink-0"></i>
          <div class="flex-1">
            <h3 class="font-bold text-green-900 dark:text-green-100 mb-2">Accès OpenWRT</h3>
            <p class="text-green-800 dark:text-green-200 text-sm mb-3">
              Votre routeur OpenWRT est prêt et accessible.
            </p>
            <Button
              label="Ouvrir l'interface OpenWRT"
              icon="pi pi-external-link"
              severity="success"
              @click="openOpenwrt"
            />
          </div>
        </div>
      </Card>

      <!-- Student Info (if available) -->
      <Card v-if="labData.student_name" class="p-6">
        <h2 class="text-xl font-bold mb-4 flex items-center gap-2">
          <i class="pi pi-user text-primary-600"></i>
          Informations Étudiant
        </h2>
        <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <div class="text-sm text-surface-500 dark:text-surface-400 mb-1">Nom</div>
            <div class="text-lg font-semibold">{{ labData.student_name }}</div>
          </div>
          <div>
            <div class="text-sm text-surface-500 dark:text-surface-400 mb-1">Email</div>
            <div class="text-sm font-mono">{{ labData.student_email || '—' }}</div>
          </div>
          <div>
            <div class="text-sm text-surface-500 dark:text-surface-400 mb-1">Promotion</div>
            <div class="text-sm">{{ labData.student_cohort || '—' }}</div>
          </div>
        </div>
      </Card>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useToast } from 'primevue/usetoast'
import {
  Card,
  Button,
  ProgressSpinner,
} from 'primevue'

interface LabInfo {
  id: string
  status: string
  created_at: string
  cluster_name?: string
  wan_ip?: string
  vxlan_tag?: number | null
  subnet?: string
  vm_count?: number
  openwrt_url?: string
  student_name?: string
  student_email?: string
  student_cohort?: string
}

interface Props {
  labData?: LabInfo
  loading?: boolean
  error?: string | null
}

const props = withDefaults(defineProps<Props>(), {
  loading: false,
  error: null,
})

defineEmits<{
  'create-lab': []
}>()

const toast = useToast()

function formatStatus(status: string): string {
  const statusMap: Record<string, string> = {
    'running': 'En cours',
    'ready': 'Prêt',
    'failed': 'Erreur',
    'creating': 'Création',
    'stopped': 'Arrêté',
  }
  return statusMap[status.toLowerCase()] || status
}

function getStatusColor(status: string): string {
  const colorMap: Record<string, string> = {
    'running': '#ef4444',
    'ready': '#22c55e',
    'failed': '#dc2626',
    'creating': '#f59e0b',
    'stopped': '#6b7280',
  }
  return colorMap[status.toLowerCase()] || '#gray'
}

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

function openOpenwrt() {
  if (props.labData?.openwrt_url) {
    window.open(props.labData.openwrt_url, '_blank')
  }
}
</script>
