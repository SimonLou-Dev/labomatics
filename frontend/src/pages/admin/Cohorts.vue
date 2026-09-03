<template>
  <div class="min-h-screen bg-surface-900 dark:bg-surface-50 p-6">
    <h1 class="text-3xl font-bold mb-6">Gestion des Promotions</h1>

    <DataTable
      :value="cohorts"
      dataKey="id"
      :rows="pageSize"
      :rowsPerPageOptions="[5, 10, 20, 50]"
      :totalRecords="totalRecords"
      :loading="loading"
      paginator
      @page="onPageChange"
    >
      <template #empty>Aucune promotion trouvée</template>

      <Column field="name" header="Nom" style="width: 25%">
        <template #body="{ data }">
          <span class="font-semibold">{{ data.name }}</span>
        </template>
      </Column>

      <Column field="year" header="Année" style="width: 10%">
        <template #body="{ data }">
          <span class="font-mono">{{ data.year }}</span>
        </template>
      </Column>

      <Column field="is_active" header="Statut" style="width: 10%">
        <template #body="{ data }">
          <Badge :value="data.is_active ? 'Actif' : 'Inactif'" :severity="data.is_active ? 'success' : 'secondary'" />
        </template>
      </Column>

      <Column field="default_cluster" header="Cluster par défaut" style="width: 20%">
        <template #body="{ data }">
          <Badge
            v-if="getDefaultCluster(data)"
            :value="getDefaultCluster(data)?.name || '—'"
            severity="success"
          />
          <span v-else class="text-surface-400">Aucun</span>
        </template>
      </Column>

      <Column field="cluster_count" header="Nb clusters" style="width: 10%">
        <template #body="{ data }">
          <span class="font-mono">{{ data.clusters?.length || 0 }}</span>
        </template>
      </Column>

      <Column field="actions" header="Actions" style="width: 15%">
        <template #body="{ data }">
          <div class="flex gap-2">
            <Button
              icon="pi pi-cog"
              severity="secondary"
              size="small"
              @click="openManageDialog(data)"
            />
          </div>
        </template>
      </Column>
    </DataTable>

    <!-- Manage Clusters Modal -->
    <Dialog
      v-model:visible="showManageDialog"
      header="Gérer les clusters"
      modal
      :style="{ width: '100vw', maxWidth: '700px' }"
    >
      <div v-if="editingCohort" class="space-y-6">
        <div>
          <h3 class="font-semibold mb-4">
            Promotion: <span class="text-primary-600">{{ editingCohort.name }}</span>
          </h3>
        </div>

        <!-- Assigned Clusters -->
        <div>
          <label class="block text-sm font-medium mb-3">Clusters assignés</label>
          <div v-if="editingCohort.clusters.length > 0" class="space-y-2 mb-4">
            <div
              v-for="cluster in editingCohort.clusters"
              :key="cluster.id"
              class="flex items-center justify-between border border-surface-200 dark:border-surface-700 rounded-lg p-3"
            >
              <span class="font-medium">{{ cluster.name }}</span>
              <div class="flex gap-2">
                <Button
                  v-if="cluster.is_default"
                  icon="pi pi-star-fill"
                  severity="success"
                  size="small"
                  text
                />
                <Button
                  v-else
                  icon="pi pi-star"
                  severity="secondary"
                  size="small"
                  text
                  @click="handleSetDefault(cluster.id)"
                />
                <Button
                  icon="pi pi-trash"
                  severity="danger"
                  size="small"
                  text
                  @click="handleRemoveCluster(cluster.id)"
                />
              </div>
            </div>
          </div>
          <div v-else class="text-surface-400 p-3 mb-4">Aucun cluster assigné</div>
        </div>

        <!-- Available Clusters to Add -->
        <div>
          <label class="block text-sm font-medium mb-3">Ajouter un cluster</label>
          <div class="flex gap-2">
            <Select
              v-model="selectedClusterToAdd"
              :options="availableClustersForAdd"
              optionLabel="name"
              optionValue="id"
              placeholder="Sélectionner un cluster"
              class="flex-1"
            />
            <Button
              label="Ajouter"
              severity="success"
              @click="handleAddCluster"
              :loading="addingCluster"
            />
          </div>
        </div>
      </div>

      <template #footer>
        <Button
          label="Fermer"
          severity="secondary"
          @click="showManageDialog = false"
        />
      </template>
    </Dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import {
  DataTable,
  Column,
  Button,
  Dialog,
  Badge,
  Select,
} from 'primevue'
import type { ClusterDTO } from '@/api/types'
import type { CohortDTO, CohortListResponseDTO } from '@/api/types/cohorts'
import * as cohortsApi from '@/api/cohorts'
import * as clustersApi from '@/api/clusters'

const cohorts = ref<CohortDTO[]>([])
const allClusters = ref<ClusterDTO[]>([])
const totalRecords = ref(0)
const loading = ref(false)
const currentPage = ref(1)
const pageSize = ref(20)

const showManageDialog = ref(false)
const editingCohort = ref<CohortDTO | null>(null)
const selectedClusterToAdd = ref<string | null>(null)
const addingCluster = ref(false)

const availableClustersForAdd = computed(() => {
  if (!editingCohort.value) return []
  const assignedIds = new Set(editingCohort.value.clusters.map((c) => c.id))
  return allClusters.value.filter((c) => !assignedIds.has(c.id))
})

function getDefaultCluster(cohort: CohortDTO) {
  return cohort.clusters?.find((c) => c.is_default)
}

async function handleSetDefault(clusterId: string) {
  if (!editingCohort.value) return
  try {
    const result = await cohortsApi.setDefaultCluster(editingCohort.value.id, clusterId)
    editingCohort.value = result
  } catch (err) {
    console.error('Failed to set default cluster:', err)
  }
}

async function handleRemoveCluster(clusterId: string) {
  if (!editingCohort.value) return
  try {
    await cohortsApi.removeClusterFromCohort(editingCohort.value.id, clusterId)
    editingCohort.value.clusters = editingCohort.value.clusters.filter((c) => c.id !== clusterId)
  } catch (err) {
    console.error('Failed to remove cluster:', err)
  }
}

async function handleAddCluster() {
  if (!editingCohort.value || !selectedClusterToAdd.value) return
  addingCluster.value = true
  try {
    const result = await cohortsApi.assignClusterToCohort(editingCohort.value.id, selectedClusterToAdd.value)
    editingCohort.value = result
    selectedClusterToAdd.value = null
  } catch (err) {
    console.error('Failed to add cluster:', err)
  } finally {
    addingCluster.value = false
  }
}

async function openManageDialog(cohort: CohortDTO) {
  editingCohort.value = { ...cohort }
  if (allClusters.value.length === 0) {
    await loadAllClusters()
  }
  showManageDialog.value = true
}

async function loadAllClusters() {
  try {
    const response = await clustersApi.listClusters(1, 100)
    allClusters.value = response.items
  } catch (err) {
    console.error('Failed to load clusters:', err)
  }
}

async function fetchCohorts(page: number = 1) {
  loading.value = true
  try {
    const response: CohortListResponseDTO = await cohortsApi.listCohorts(page, pageSize.value)
    cohorts.value = response.items
    totalRecords.value = response.total
    currentPage.value = page
  } catch (err) {
    console.error('Failed to fetch cohorts:', err)
  } finally {
    loading.value = false
  }
}

function onPageChange(event: any) {
  const newPage = event.page + 1
  fetchCohorts(newPage)
}

onMounted(() => {
  fetchCohorts()
})
</script>
