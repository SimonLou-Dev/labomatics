<template>
  <div class="min-h-screen bg-surface-900 dark:bg-surface-50 p-6">
    <div class="mb-6 flex justify-between items-center">
      <h1 class="text-3xl font-bold">Plages IP WAN</h1>
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
      :value="ipRanges"
      dataKey="id"
      :totalRecords="totalRecords"
      :loading="loading"
      @page="onPageChange"
    >
      <template #empty>Aucune plage IP trouvée</template>
      <Column field="name" header="Nom" style="width: 20%">
        <template #body="{ data }">
          <span class="font-semibold">{{ data.name }}</span>
        </template>
      </Column>
      <Column field="network" header="Réseau" style="width: 18%">
        <template #body="{ data }">
          <span class="font-mono">{{ data.network }}</span>
        </template>
      </Column>
      <Column field="utilization" header="Utilisation" style="width: 18%">
        <template #body="{ data }">
          <div class="flex items-center gap-2">
            <div class="flex-1 h-6 border border-surface-400 bg-surface-700 rounded"
              :style="{
                background: `linear-gradient(90deg, ${getProgressBarColor(data)} 0%, ${getProgressBarColor(data)} ${getUtilizationPercent(data)}%, var(--surface-700) ${getUtilizationPercent(data)}%, var(--surface-700) 100%)`
              }"
            />
            <span class="text-xs font-medium w-12 text-right">
              {{ getUtilizationPercent(data) }}%
            </span>
          </div>
        </template>
      </Column>
      <Column field="gateway" header="Passerelle" style="width: 13%">
        <template #body="{ data }">
          <span class="font-mono">{{ data.gateway }}</span>
        </template>
      </Column>
      <Column field="exclusions" header="Exclusions" style="width: 20%">
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
      :header="editingRange ? 'Éditer la plage IP' : 'Créer une plage IP'"
      modal
      :style="{ width: '100vw', maxWidth: '600px' }"
    >
      <div class="space-y-4">
        <div>
          <label class="block text-sm font-medium mb-2">Nom</label>
          <InputText
            v-model="formData.name"
            class="w-full"
            placeholder="ex: eth-lab-wan"
          />
        </div>
        <div>
          <label class="block text-sm font-medium mb-2">Réseau (CIDR)</label>
          <InputText
            v-model="formData.network"
            class="w-full"
            placeholder="ex: 192.168.1.0/24"
          />
        </div>
        <div>
          <label class="block text-sm font-medium mb-2">Passerelle</label>
          <InputText
            v-model="formData.gateway"
            class="w-full"
            placeholder="ex: 192.168.1.1"
          />
        </div>
        <div>
          <label class="block text-sm font-medium mb-2">Exclusions (une par ligne)</label>
          <Textarea
            v-model="exclusionsText"
            class="w-full"
            rows="4"
            placeholder="ex: 192.168.1.1&#10;192.168.1.2&#10;192.168.1.255"
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
  Chip,
  Textarea,
  ProgressBar,
} from 'primevue'
import type { IpRangeDTO, IpRangeCreateDTO } from '@/api/types'
import * as ipRangeApi from '@/api/ipRanges'

const router = useRouter()
const toast = useToast()
const confirm = useConfirm()

const ipRanges = ref<IpRangeDTO[]>([])
const totalRecords = ref(0)
const loading = ref(false)
const currentPage = ref(1)
const pageSize = ref(10)

const showFormDialog = ref(false)
const editingRange = ref<IpRangeDTO | null>(null)
const formLoading = ref(false)
const exclusionsText = ref('')
const formData = ref<IpRangeCreateDTO>({
  name: '',
  network: '',
  gateway: '',
  exclusions: [],
})

function getUtilizationPercent(range: IpRangeDTO): number {
  return range.utilization_percent
}

function getProgressBarColor(range: IpRangeDTO): string {
  const percent = getUtilizationPercent(range)
  if (percent >= 80) return 'var(--red-500)'
  if (percent >= 50) return 'var(--orange-500)'
  return 'var(--orange-500)'
}

async function fetchIpRanges(page: number = 1) {
  loading.value = true
  try {
    const response = await ipRangeApi.listIpRanges(page, pageSize.value)
    ipRanges.value = response.items
    totalRecords.value = response.total
    currentPage.value = page
  } catch (error) {
    toast.add({
      severity: 'error',
      summary: 'Erreur',
      detail: 'Impossible de charger les plages IP',
      life: 3000,
    })
    console.error('Failed to fetch IP ranges:', error)
  } finally {
    loading.value = false
  }
}

function onPageChange(event: any) {
  const newPage = Math.floor(event.first / event.rows) + 1
  fetchIpRanges(newPage)
}

function goToDetails(range: IpRangeDTO) {
  router.push(`/admin/wan/${range.id}`)
}

function openCreateDialog() {
  editingRange.value = null
  formData.value = {
    name: '',
    network: '',
    gateway: '',
    exclusions: [],
  }
  exclusionsText.value = ''
  showFormDialog.value = true
}

function openEditDialog(range: IpRangeDTO) {
  editingRange.value = range
  formData.value = {
    name: range.name,
    network: range.network,
    gateway: range.gateway,
    exclusions: range.exclusions,
  }
  exclusionsText.value = range.exclusions.join('\n')
  showFormDialog.value = true
}

async function saveRange() {
  formLoading.value = true
  try {
    const dataToSave: IpRangeCreateDTO = {
      ...formData.value,
      exclusions: exclusionsText.value
        .split('\n')
        .map((line) => line.trim())
        .filter((line) => line.length > 0),
    }

    if (editingRange.value) {
      await ipRangeApi.updateIpRange(editingRange.value.id, dataToSave)
      toast.add({
        severity: 'success',
        summary: 'Succès',
        detail: 'Plage IP mise à jour',
        life: 3000,
      })
    } else {
      await ipRangeApi.createIpRange(dataToSave)
      toast.add({
        severity: 'success',
        summary: 'Succès',
        detail: 'Plage IP créée',
        life: 3000,
      })
    }
    showFormDialog.value = false
    await fetchIpRanges(currentPage.value)
  } catch (error) {
    toast.add({
      severity: 'error',
      summary: 'Erreur',
      detail: 'Impossible de sauvegarder la plage IP',
      life: 3000,
    })
    console.error('Failed to save IP range:', error)
  } finally {
    formLoading.value = false
  }
}

function confirmDeleteRange(range: IpRangeDTO) {
  confirm.require({
    message: `Êtes-vous sûr de vouloir supprimer la plage "${range.name}" ?`,
    header: 'Confirmation',
    icon: 'pi pi-exclamation-triangle',
    accept: () => deleteRange(range.id),
  })
}

async function deleteRange(id: string) {
  try {
    await ipRangeApi.deleteIpRange(id)
    toast.add({
      severity: 'success',
      summary: 'Succès',
      detail: 'Plage IP supprimée',
      life: 3000,
    })
    await fetchIpRanges(currentPage.value)
  } catch (error) {
    toast.add({
      severity: 'error',
      summary: 'Erreur',
      detail: 'Impossible de supprimer la plage IP',
      life: 3000,
    })
    console.error('Failed to delete IP range:', error)
  }
}

onMounted(() => {
  fetchIpRanges()
})
</script>
