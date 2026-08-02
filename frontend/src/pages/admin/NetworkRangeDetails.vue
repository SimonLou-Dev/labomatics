<template>
  <div class="min-h-screen bg-surface-900 dark:bg-surface-50 p-6">
    <div class="mb-6">
      <Button
        label="Retour"
        icon="pi pi-arrow-left"
        severity="secondary"
        @click="goBack"
        class="mb-4"
      />
      <h1 v-if="range" class="text-3xl font-bold">{{ range.name }}</h1>
      <p v-if="range" class="text-surface-400 mt-2">
        Réseau: {{ range.base_network }} • MTU: {{ range.mtu }} • VNI: {{ range.vni_min }} - {{ range.vni_max }}
      </p>
    </div>

    <!-- Métriques -->
    <div v-if="range" class="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
      <Card class="p-6">
        <div class="text-sm text-surface-500 dark:text-surface-400 mb-2">Utilisation VNI</div>
        <div class="flex items-end justify-between">
          <div>
            <div class="text-2xl font-bold">{{ utilizationPercent }}%</div>
            <div class="text-sm text-surface-400">{{ vniCountUsed }} / {{ totalVnis }} VNIs</div>
          </div>
          <ProgressBar
            :value="utilizationPercent"
            class="flex-1 ml-4 h-8"
            :style="{ backgroundColor: 'var(--surface-200)' }"
          />
        </div>
      </Card>

      <Card class="p-6">
        <div class="text-sm text-surface-500 dark:text-surface-400 mb-2">VNIs Libres</div>
        <div class="text-2xl font-bold">{{ vnisFree }}</div>
      </Card>

      <Card class="p-6">
        <div class="text-sm text-surface-500 dark:text-surface-400 mb-2">Statut</div>
        <div class="flex items-center gap-2">
          <i
            :class="statusIcon"
            :style="{ color: statusColor }"
          />
          <span :style="{ color: statusColor }">{{ statusLabel }}</span>
        </div>
      </Card>
    </div>

    <!-- Barre de progression -->
    <div v-if="range" class="mb-6">
      <div class="flex items-center gap-4">
        <ProgressBar
          :value="utilizationPercent"
          class="flex-1 h-6"
          :style="{ backgroundColor: progressBarBackground }"
        />
        <span class="text-sm font-medium w-20">{{ utilizationPercent }}%</span>
      </div>
      <div class="flex gap-6 mt-3 text-xs">
        <div class="flex items-center gap-2">
          <div class="w-3 h-3 rounded-full" style="background-color: var(--green-500)"></div>
          <span>&lt; 50%</span>
        </div>
        <div class="flex items-center gap-2">
          <div class="w-3 h-3 rounded-full" style="background-color: var(--yellow-500)"></div>
          <span>50-80%</span>
        </div>
        <div class="flex items-center gap-2">
          <div class="w-3 h-3 rounded-full" style="background-color: var(--red-500)"></div>
          <span>&gt; 80%</span>
        </div>
      </div>
    </div>

    <!-- Allocations Table -->
    <Card v-if="range" class="p-6">
      <h2 class="text-xl font-bold mb-4">Allocations VXLAN</h2>
      <DataTable
        paginator
        :rows="pageSize"
        :rowsPerPageOptions="[5, 10, 20]"
        :value="allocations"
        dataKey="vni"
        :loading="allocationsLoading"
        :totalRecords="allocations.length"
      >
        <template #empty>Aucune allocation trouvée</template>
        <Column field="vni" header="VNI" style="width: 15%">
          <template #body="{ data }">
            <span class="font-mono font-bold">{{ data.vni }}</span>
          </template>
        </Column>
        <Column field="student_login" header="Login" style="width: 15%">
          <template #body="{ data }">
            <span class="font-semibold">{{ data.student_login }}</span>
          </template>
        </Column>
        <Column field="student_first_name" header="Prénom" style="width: 15%">
          <template #body="{ data }">
            <span>{{ data.student_first_name }}</span>
          </template>
        </Column>
        <Column field="student_last_name" header="Nom" style="width: 15%">
          <template #body="{ data }">
            <span>{{ data.student_last_name }}</span>
          </template>
        </Column>
        <Column field="openwrt_link" header="OpenWRT" style="width: 20%">
          <template #body="{ data }">
            <a
              v-if="data.openwrt_link"
              :href="data.openwrt_link"
              target="_blank"
              class="text-blue-500 hover:underline flex items-center gap-1"
            >
              <i class="pi pi-external-link" style="font-size: 0.75rem"></i>
              Accéder
            </a>
            <span v-else class="text-surface-400">—</span>
          </template>
        </Column>
        <Column field="actions" header="Actions" style="width: 15%" frozen align-frozen="right">
          <template #body="{ data }">
            <Button
              icon="pi pi-arrow-right"
              severity="info"
              size="small"
              v-tooltip="'Voir le lab étudiant'"
              @click="goToStudentLab(data.student_login)"
            />
          </template>
        </Column>
      </DataTable>
    </Card>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useToast } from 'primevue/usetoast'
import {
  Card,
  DataTable,
  Column,
  Button,
  ProgressBar,
} from 'primevue'
import type { VxlanRangeDTO, VxlanAllocationDTO } from '@/api/types'
import * as vxlanRangeApi from '@/api/vxlanRanges'

const router = useRouter()
const route = useRoute()
const toast = useToast()

const range = ref<VxlanRangeDTO | null>(null)
const allocations = ref<VxlanAllocationDTO[]>([])
const loading = ref(false)
const allocationsLoading = ref(false)
const pageSize = ref(10)

const totalVnis = computed(() => {
  if (!range.value) return 0
  return range.value.vni_max - range.value.vni_min + 1
})

const vniCountUsed = computed(() => allocations.value.length)
const vnisFree = computed(() => Math.max(0, totalVnis.value - vniCountUsed.value))
const utilizationPercent = computed(() => {
  if (totalVnis.value === 0) return 0
  return Math.round((vniCountUsed.value / totalVnis.value) * 100)
})

const statusLabel = computed(() => {
  if (utilizationPercent.value >= 80) return 'Critique'
  if (utilizationPercent.value >= 50) return 'Attention'
  return 'Normal'
})

const statusIcon = computed(() => {
  if (utilizationPercent.value >= 80) return 'pi pi-exclamation-circle'
  if (utilizationPercent.value >= 50) return 'pi pi-bell'
  return 'pi pi-check-circle'
})

const statusColor = computed(() => {
  if (utilizationPercent.value >= 80) return 'var(--red-500)'
  if (utilizationPercent.value >= 50) return 'var(--yellow-500)'
  return 'var(--green-500)'
})

const progressBarBackground = computed(() => {
  if (utilizationPercent.value >= 80) return 'var(--red-500)'
  if (utilizationPercent.value >= 50) return 'var(--yellow-500)'
  return 'var(--green-500)'
})

async function fetchRange() {
  loading.value = true
  try {
    const rangeId = route.params.rangeId as string
    // Note: This assumes a getVxlanRange method exists in the API
    // For now, we'll fetch all ranges and find the one matching
    const response = await vxlanRangeApi.listVxlanRanges(1, 100)
    const found = response.items.find((r) => r.id === rangeId)
    if (found) {
      range.value = found
      await fetchAllocations()
    } else {
      toast.add({
        severity: 'error',
        summary: 'Erreur',
        detail: 'Plage VXLAN non trouvée',
        life: 3000,
      })
      goBack()
    }
  } catch (error) {
    toast.add({
      severity: 'error',
      summary: 'Erreur',
      detail: 'Impossible de charger la plage VXLAN',
      life: 3000,
    })
    console.error('Failed to fetch VXLAN range:', error)
  } finally {
    loading.value = false
  }
}

async function fetchAllocations() {
  if (!range.value) return
  allocationsLoading.value = true
  try {
    allocations.value = await vxlanRangeApi.getVxlanRangeAllocations(range.value.id)
  } catch (error) {
    toast.add({
      severity: 'error',
      summary: 'Erreur',
      detail: 'Impossible de charger les allocations',
      life: 3000,
    })
    console.error('Failed to fetch allocations:', error)
  } finally {
    allocationsLoading.value = false
  }
}

function goBack() {
  router.push('/admin/networks')
}

function goToStudentLab(studentLogin: string) {
  router.push(`/lab/${studentLogin}`)
}

onMounted(() => {
  fetchRange()
})
</script>
