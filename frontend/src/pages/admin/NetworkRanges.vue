<template>
  <div class="min-h-screen bg-surface-900 dark:bg-surface-50 p-6">
    <div class="mb-6 flex justify-between items-center">
      <h1 class="text-3xl font-bold">Plages VXLAN Étudiants</h1>
      <Button
        label="Créer"
        icon="pi pi-plus"
        @click="openCreateDialog"
      />
    </div>

    <DataTable
      paginator
      :rows="pageSize"
      :rowsPerPageOptions="[5, 10, 20, 50]"
      :value="vxlanRanges"
      dataKey="id"
      :totalRecords="totalRecords"
      :loading="loading"
      @page="onPageChange"
    >
      <template #empty>Aucune plage VXLAN trouvée</template>
      <Column field="name" header="Nom" style="width: 15%">
        <template #body="{ data }">
          <span class="font-semibold">{{ data.name }}</span>
        </template>
      </Column>
      <Column field="base_network" header="Réseau Base" style="width: 13%">
        <template #body="{ data }">
          <span class="font-mono">{{ data.base_network }}</span>
        </template>
      </Column>
      <Column field="utilization" header="Utilisation" style="width: 15%">
        <template #body="{ data }">
          <div class="flex items-center gap-2">
            <ProgressBar
              :value="getUtilizationPercent(data)"
              class="flex-1 h-6 border border-surface-400"
              :style="{ backgroundColor: 'var(--surface-700)' }"
            >
              <template #default="{ value }">
                <div
                  :style="{
                    width: value + '%',
                    height: '100%',
                    backgroundColor: getProgressBarColor(data),
                    transition: 'width 0.3s ease',
                  }"
                />
              </template>
            </ProgressBar>
            <span class="text-xs font-medium w-12 text-right">
              {{ getUtilizationPercent(data) }}%
            </span>
          </div>
        </template>
      </Column>
      <Column field="mtu" header="MTU" style="width: 8%">
        <template #body="{ data }">
          <span class="font-mono">{{ data.mtu }}</span>
        </template>
      </Column>
      <Column field="vni_min" header="VNI Min" style="width: 8%">
        <template #body="{ data }">
          <span class="font-mono">{{ data.vni_min }}</span>
        </template>
      </Column>
      <Column field="vni_max" header="VNI Max" style="width: 8%">
        <template #body="{ data }">
          <span class="font-mono">{{ data.vni_max }}</span>
        </template>
      </Column>
      <Column field="exclusions" header="Exclusions VNI" style="width: 18%">
        <template #body="{ data }">
          <div v-if="data.exclusions.length > 0" class="flex flex-wrap gap-1">
            <Chip
              v-for="(excl, idx) in data.exclusions"
              :key="idx"
              :label="excl"
              class="text-xs"
            />
          </div>
          <span v-else class="text-surface-400">—</span>
        </template>
      </Column>
      <Column field="actions" header="Actions" style="width: 21%" frozen align-frozen="right">
        <template #body="{ data }">
          <div class="flex gap-2">
            <Button
              icon="pi pi-arrow-right"
              severity="info"
              size="small"
              v-tooltip="'Consulter'"
              @click="goToDetails(data)"
            />
            <Button
              icon="pi pi-pencil"
              severity="secondary"
              size="small"
              v-tooltip="'Éditer'"
              @click="openEditDialog(data)"
            />
            <Button
              icon="pi pi-trash"
              severity="danger"
              size="small"
              v-tooltip="'Supprimer'"
              @click="confirmDeleteRange(data)"
            />
          </div>
        </template>
      </Column>
    </DataTable>

    <!-- Create/Edit Dialog -->
    <Dialog
      v-model:visible="showFormDialog"
      :header="editingRange ? 'Éditer la plage VXLAN' : 'Créer une plage VXLAN'"
      modal
      :style="{ width: '100vw', maxWidth: '600px' }"
    >
      <div class="space-y-4">
        <div>
          <label class="block text-sm font-medium mb-2">Nom</label>
          <InputText
            v-model="formData.name"
            class="w-full"
            placeholder="ex: vxlan-students"
          />
        </div>
        <div>
          <label class="block text-sm font-medium mb-2">Réseau Base (CIDR)</label>
          <InputText
            v-model="formData.base_network"
            class="w-full"
            placeholder="ex: 10.0.0.0/8"
          />
        </div>
        <div>
          <label class="block text-sm font-medium mb-2">MTU</label>
          <InputNumber
            v-model.number="formData.mtu"
            class="w-full"
            placeholder="ex: 1450"
          />
        </div>
        <div>
          <label class="block text-sm font-medium mb-2">VNI Min</label>
          <InputNumber
            v-model.number="formData.vni_min"
            class="w-full"
            placeholder="ex: 100"
          />
        </div>
        <div>
          <label class="block text-sm font-medium mb-2">VNI Max</label>
          <InputNumber
            v-model.number="formData.vni_max"
            class="w-full"
            placeholder="ex: 1000"
          />
        </div>
        <div>
          <label class="block text-sm font-medium mb-2">Exclusions VNI (une par ligne)</label>
          <Textarea
            v-model="exclusionsText"
            class="w-full"
            rows="4"
            placeholder="ex: 100&#10;101&#10;102"
          />
        </div>
      </div>

      <template #footer>
        <Button
          label="Annuler"
          severity="secondary"
          @click="showFormDialog = false"
        />
        <Button
          :label="editingRange ? 'Mettre à jour' : 'Créer'"
          :loading="formLoading"
          @click="saveRange"
        />
      </template>
    </Dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useToast } from 'primevue/usetoast'
import { useConfirm } from 'primevue/useconfirm'
import {
  DataTable,
  Column,
  Dialog,
  Button,
  InputText,
  InputNumber,
  Chip,
  Textarea,
  ProgressBar,
} from 'primevue'
import type { VxlanRangeDTO, VxlanRangeCreateDTO } from '@/api/types'
import * as vxlanRangeApi from '@/api/vxlanRanges'

const router = useRouter()
const toast = useToast()
const confirm = useConfirm()

const vxlanRanges = ref<VxlanRangeDTO[]>([])
const totalRecords = ref(0)
const loading = ref(false)
const currentPage = ref(1)
const pageSize = ref(10)
const allocationCounts = ref<Record<string, number>>({})

const showFormDialog = ref(false)
const editingRange = ref<VxlanRangeDTO | null>(null)
const formLoading = ref(false)
const exclusionsText = ref('')
const formData = ref<VxlanRangeCreateDTO>({
  name: '',
  base_network: '',
  mtu: 1450,
  vni_min: 0,
  vni_max: 16777215,
  exclusions: [],
})

function getUtilizationPercent(range: VxlanRangeDTO): number {
  const total = range.vni_max - range.vni_min + 1
  const used = allocationCounts.value[range.id] || 0
  if (total === 0) return 0
  return Math.round((used / total) * 100)
}

function getProgressBarColor(range: VxlanRangeDTO): string {
  const percent = getUtilizationPercent(range)
  if (percent >= 80) return 'var(--red-500)'
  if (percent >= 50) return 'var(--orange-500)'
  return 'var(--orange-500)'
}

async function fetchVxlanRanges(page: number = 1) {
  loading.value = true
  try {
    const response = await vxlanRangeApi.listVxlanRanges(page, pageSize.value)
    vxlanRanges.value = response.items
    totalRecords.value = response.total
    currentPage.value = page

    // Load allocation counts for each range
    for (const range of response.items) {
      try {
        const allocations = await vxlanRangeApi.getVxlanRangeAllocations(range.id)
        allocationCounts.value[range.id] = allocations.length
      } catch (error) {
        console.error(`Failed to load allocations for range ${range.id}:`, error)
        allocationCounts.value[range.id] = 0
      }
    }
  } catch (error) {
    toast.add({
      severity: 'error',
      summary: 'Erreur',
      detail: 'Impossible de charger les plages VXLAN',
      life: 3000,
    })
    console.error('Failed to fetch VXLAN ranges:', error)
  } finally {
    loading.value = false
  }
}

function onPageChange(event: any) {
  const newPage = Math.floor(event.first / event.rows) + 1
  fetchVxlanRanges(newPage)
}

function goToDetails(range: VxlanRangeDTO) {
  router.push(`/admin/networks/${range.id}`)
}

function openCreateDialog() {
  editingRange.value = null
  formData.value = {
    name: '',
    base_network: '',
    mtu: 1450,
    vni_min: 0,
    vni_max: 16777215,
    exclusions: [],
  }
  exclusionsText.value = ''
  showFormDialog.value = true
}

function openEditDialog(range: VxlanRangeDTO) {
  editingRange.value = range
  formData.value = {
    name: range.name,
    base_network: range.base_network,
    mtu: range.mtu,
    vni_min: range.vni_min,
    vni_max: range.vni_max,
    exclusions: range.exclusions,
  }
  exclusionsText.value = range.exclusions.join('\n')
  showFormDialog.value = true
}

async function saveRange() {
  formLoading.value = true
  try {
    const dataToSave: VxlanRangeCreateDTO = {
      ...formData.value,
      exclusions: exclusionsText.value
        .split('\n')
        .map((line) => line.trim())
        .filter((line) => line.length > 0),
    }

    if (editingRange.value) {
      await vxlanRangeApi.updateVxlanRange(editingRange.value.id, dataToSave)
      toast.add({
        severity: 'success',
        summary: 'Succès',
        detail: 'Plage VXLAN mise à jour',
        life: 3000,
      })
    } else {
      await vxlanRangeApi.createVxlanRange(dataToSave)
      toast.add({
        severity: 'success',
        summary: 'Succès',
        detail: 'Plage VXLAN créée',
        life: 3000,
      })
    }
    showFormDialog.value = false
    await fetchVxlanRanges(currentPage.value)
  } catch (error) {
    toast.add({
      severity: 'error',
      summary: 'Erreur',
      detail: 'Impossible de sauvegarder la plage VXLAN',
      life: 3000,
    })
    console.error('Failed to save VXLAN range:', error)
  } finally {
    formLoading.value = false
  }
}

function confirmDeleteRange(range: VxlanRangeDTO) {
  confirm.require({
    message: `Êtes-vous sûr de vouloir supprimer la plage "${range.name}" ?`,
    header: 'Confirmation',
    icon: 'pi pi-exclamation-triangle',
    accept: () => deleteRange(range.id),
  })
}

async function deleteRange(id: string) {
  try {
    await vxlanRangeApi.deleteVxlanRange(id)
    toast.add({
      severity: 'success',
      summary: 'Succès',
      detail: 'Plage VXLAN supprimée',
      life: 3000,
    })
    await fetchVxlanRanges(currentPage.value)
  } catch (error) {
    toast.add({
      severity: 'error',
      summary: 'Erreur',
      detail: 'Impossible de supprimer la plage VXLAN',
      life: 3000,
    })
    console.error('Failed to delete VXLAN range:', error)
  }
}

onMounted(() => {
  fetchVxlanRanges()
})
</script>
