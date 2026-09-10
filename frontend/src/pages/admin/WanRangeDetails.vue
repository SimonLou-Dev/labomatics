<template>
  <div class="min-h-screen bg-surface-900 dark:bg-surface-50 p-6">
    <div class="mb-6">
      <Button
        label="Retour"
        icon="pi pi-arrow-left"
        severity="secondary"
        class="mb-4"
        @click="goBack"
      />
      <h1
        v-if="range"
        class="text-3xl font-bold"
      >
        {{ range.name }}
      </h1>
      <p
        v-if="range"
        class="text-surface-400 mt-2"
      >
        {{ range.network }} • Passerelle: {{ range.gateway }}
      </p>
    </div>

    <!-- Métriques -->
    <div
      v-if="range"
      class="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6"
    >
      <Card class="p-6">
        <template #content>
          <div class="text-sm text-surface-500 dark:text-surface-400 mb-2">
            Utilisation
          </div>
          <div class="flex items-end justify-between">
            <div>
              <div class="text-2xl font-bold">
                {{ range.utilization_percent }}%
              </div>
              <div class="text-sm text-surface-400">
                {{ range.used_count }} / {{ range.total_ips }} IPs
              </div>
            </div>
            <ProgressBar
              :value="range.utilization_percent"
              class="flex-1 ml-4 h-8"
              :style="{ backgroundColor: 'var(--surface-200)' }"
            />
          </div>
        </template>
      </Card>

      <Card class="p-6">
        <template #content>
          <div class="text-sm text-surface-500 dark:text-surface-400 mb-2">
            IPs Libres
          </div>
          <div class="text-2xl font-bold">
            {{ range.free_count }}
          </div>
        </template>
      </Card>

      <Card class="p-6">
        <template #content>
          <div class="text-sm text-surface-500 dark:text-surface-400 mb-2">
            Statut
          </div>
          <div class="flex items-center gap-2">
            <i
              :class="statusIcon"
              :style="{ color: statusColor }"
            />
            <span :style="{ color: statusColor }">{{ statusLabel }}</span>
          </div>
        </template>
      </Card>
    </div>

    <!-- Barre de progression -->
    <div
      v-if="range"
      class="mb-6"
    >
      <div class="flex items-center gap-4">
        <ProgressBar
          :value="range.utilization_percent"
          class="flex-1 h-6"
          :style="{ backgroundColor: progressBarBackground }"
        />
        <span class="text-sm font-medium w-20">{{ range.utilization_percent }}%</span>
      </div>
      <div class="flex gap-6 mt-3 text-xs">
        <div class="flex items-center gap-2">
          <div
            class="w-3 h-3 rounded-full"
            style="background-color: var(--green-500)"
          />
          <span>&lt; 50%</span>
        </div>
        <div class="flex items-center gap-2">
          <div
            class="w-3 h-3 rounded-full"
            style="background-color: var(--yellow-500)"
          />
          <span>50-80%</span>
        </div>
        <div class="flex items-center gap-2">
          <div
            class="w-3 h-3 rounded-full"
            style="background-color: var(--red-500)"
          />
          <span>&gt; 80%</span>
        </div>
      </div>
    </div>

    <!-- Allocations Table -->
    <Card
      v-if="range"
      class="p-6"
    >
      <template #content>
        <div class="flex items-center justify-between mb-4">
          <h2 class="text-xl font-bold">
            Allocations d'adresses IP
          </h2>
          <InputGroup class="w-72">
            <InputText
              v-model="searchQuery"
              placeholder="Chercher par IP ou étudiant..."
              @input="onSearchChange"
            />
            <Button
              icon="pi pi-search"
              severity="secondary"
            />
          </InputGroup>
        </div>
        <DataTable
          :value="allocationsData.items"
          data-key="ip_address"
          :loading="allocationsLoading"
          :rows="pageSize"
          :total-records="allocationsData.total"
          paginator
          :first="(currentPage - 1) * pageSize"
          :rows-per-page-options="[5, 10, 20, 50]"
          @page="onPageChange"
        >
          <template #empty>
            Aucune allocation trouvée
          </template>
          <Column
            field="ip_address"
            header="Adresse IP"
            style="width: 20%"
          >
            <template #body="{ data }">
              <span class="font-mono">{{ data.ip_address }}</span>
            </template>
          </Column>
          <Column
            field="student.login"
            header="Login"
            style="width: 15%"
          >
            <template #body="{ data }">
              <span
                v-if="data.student"
                class="font-semibold"
              >{{ data.student.login }}</span>
              <span
                v-else
                class="text-surface-400"
              >—</span>
            </template>
          </Column>
          <Column
            field="student.first_name"
            header="Prénom"
            style="width: 15%"
          >
            <template #body="{ data }">
              <span v-if="data.student">{{ data.student.first_name }}</span>
              <span
                v-else
                class="text-surface-400"
              >—</span>
            </template>
          </Column>
          <Column
            field="student.last_name"
            header="Nom"
            style="width: 15%"
          >
            <template #body="{ data }">
              <span v-if="data.student">{{ data.student.last_name }}</span>
              <span
                v-else
                class="text-surface-400"
              >—</span>
            </template>
          </Column>
          <Column
            header="Statut"
            style="width: 15%"
          >
            <template #body="{ data }">
              <Tag
                :value="data.is_taken ? 'Allouée' : 'Libre'"
                :severity="data.is_taken ? 'warning' : 'success'"
              />
            </template>
          </Column>
          <Column
            field="actions"
            header="Actions"
            style="width: 20%"
          >
            <template #body="{ data }">
              <Button
                v-if="data.student"
                v-tooltip="'Voir le lab étudiant'"
                icon="pi pi-arrow-right"
                severity="info"
                size="small"
                @click="goToStudentLab(data.student.id)"
              />
            </template>
          </Column>
        </DataTable>
      </template>
    </Card>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useToast } from 'primevue/usetoast'
import type { AxiosError } from 'axios'
import {
  Card,
  DataTable,
  Column,
  Button,
  ProgressBar,
  InputGroup,
  InputText,
  Tag,
} from 'primevue'
import type { IpRangeDTO, IpAllocationPaginatedDTO } from '@/api/types'
import * as ipRangeApi from '@/api/ipRanges'

const router = useRouter()
const route = useRoute()
const toast = useToast()

const range = ref<IpRangeDTO | null>(null)
const allocationsData = ref<IpAllocationPaginatedDTO>({
  items: [],
  total: 0,
  page: 1,
  per_page: 20,
  total_pages: 0,
})
const loading = ref(false)
const allocationsLoading = ref(false)
const pageSize = ref(20)
const currentPage = ref(1)
const searchQuery = ref('')
const searchTimeout = ref<number | null>(null)

const statusLabel = computed(() => {
  if (!range.value) return 'Normal'
  if (range.value.utilization_percent >= 80) return 'Critique'
  if (range.value.utilization_percent >= 50) return 'Attention'
  return 'Normal'
})

const statusIcon = computed(() => {
  if (!range.value) return 'pi pi-check-circle'
  if (range.value.utilization_percent >= 80) return 'pi pi-exclamation-circle'
  if (range.value.utilization_percent >= 50) return 'pi pi-bell'
  return 'pi pi-check-circle'
})

const statusColor = computed(() => {
  if (!range.value) return 'var(--green-500)'
  if (range.value.utilization_percent >= 80) return 'var(--red-500)'
  if (range.value.utilization_percent >= 50) return 'var(--yellow-500)'
  return 'var(--green-500)'
})

const progressBarBackground = computed(() => {
  if (!range.value) return 'var(--green-500)'
  if (range.value.utilization_percent >= 80) return 'var(--red-500)'
  if (range.value.utilization_percent >= 50) return 'var(--yellow-500)'
  return 'var(--green-500)'
})

async function fetchRange() {
  loading.value = true
  try {
    const rangeId = route.params.rangeId as string
    range.value = await ipRangeApi.getIpRange(rangeId)
    currentPage.value = 1
    await fetchAllocations()
  } catch (error) {
    if ((error as AxiosError).response?.status === 404) {
      toast.add({
        severity: 'error',
        summary: 'Erreur',
        detail: 'Plage IP non trouvée',
        life: 3000,
      })
      goBack()
    } else {
      toast.add({
        severity: 'error',
        summary: 'Erreur',
        detail: 'Impossible de charger la plage IP',
        life: 3000,
      })
    }
    console.error('Failed to fetch IP range:', error)
  } finally {
    loading.value = false
  }
}

async function fetchAllocations() {
  if (!range.value) return
  allocationsLoading.value = true
  try {
    allocationsData.value = await ipRangeApi.getIpRangeAllocations(
      range.value.id,
      currentPage.value,
      pageSize.value,
      searchQuery.value || undefined
    )
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

function onPageChange(event: { page: number }) {
  currentPage.value = event.page + 1
  fetchAllocations()
}

function onSearchChange() {
  currentPage.value = 1
  if (searchTimeout.value) {
    clearTimeout(searchTimeout.value)
  }
  searchTimeout.value = setTimeout(() => {
    fetchAllocations()
  }, 300)
}

function goBack() {
  router.push('/admin/wan')
}

function goToStudentLab(studentLogin: string) {
  router.push(`/lab/${studentLogin}`)
}

onMounted(() => {
  fetchRange()
})
</script>
