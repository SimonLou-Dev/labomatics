<template>
  <div class="min-h-screen bg-surface-900 dark:bg-surface-50 p-6">
    <div class="mb-6 flex justify-between items-center">
      <h1 class="text-3xl font-bold">Étudiants</h1>
      <Button
        label="Importer XML"
        icon="pi pi-upload"
        severity="info"
        @click="openImportDialog"
      />
    </div>

    <div class="mb-3 flex justify-end">
      <IconField>
        <InputIcon>
          <Search />
        </InputIcon>
        <InputText
          v-model="searchQuery"
          size="small"
          placeholder="Rechercher par nom / email"
          @keyup.enter="onSearch"
        />
      </IconField>
    </div>

    <DataTable
      paginator
      :rows="pageSize"
      :rowsPerPageOptions="[5, 10, 20, 50]"
      :value="students"
      dataKey="id"
      :totalRecords="totalRecords"
      :loading="loading"
      @page="onPageChange"
    >
      <template #empty> Aucun étudiant trouvé </template>
      <Column field="id" header="#" style="width: 8%">
        <template #body="{ data }">
          <span class="font-semibold text-sm">{{ data.id.slice(0, 8) }}</span>
        </template>
      </Column>
      <Column field="login" header="Login" style="width: 12%">
        <template #body="{ data }">
          <span class="font-semibold">{{ data.login }}</span>
        </template>
      </Column>
      <Column field="first_name" header="Nom" style="width: 15%">
        <template #body="{ data }">
          <span class="font-semibold">{{ data.first_name }} {{ data.last_name }}</span>
        </template>
      </Column>
      <Column field="email" header="Email" style="width: 18%">
        <template #body="{ data }">
          <span class="font-semibold text-sm">{{ data.email }}</span>
        </template>
      </Column>
      <Column field="cohort_name" header="Promo" style="width: 12%">
        <template #body="{ data }">
          <Badge :value="data.cohort_name" :severity="getCohortColor(data.cohort_name)" />
        </template>
      </Column>
      <Column field="wan_ip" header="IP WAN" style="width: 12%">
        <template #body="{ data }">
          <span class="font-mono text-sm" v-if="data.wan_ip">
            {{ data.wan_ip }}
          </span>
          <span v-else class="text-surface-400">—</span>
        </template>
      </Column>
      <Column field="vxlan_tag" header="VNI" style="width: 8%">
        <template #body="{ data }">
          <span class="font-mono font-semibold" v-if="data.vxlan_tag">
            {{ data.vxlan_tag }}
          </span>
          <span v-else class="text-surface-400">—</span>
        </template>
      </Column>
      <Column field="actions" header="Actions" style="width: 15%">
        <template #body="{ data }">
          <div class="flex gap-2">
            <Button
              icon="pi pi-replay"
              severity="secondary"
              size="small"
              v-tooltip="data.wan_ip ? 'Recréer le lab' : 'Déployer le lab'"
            />
            <Button
              icon="pi pi-trash"
              severity="danger"
              size="small"
              v-tooltip="'Supprimer'"
            />
          </div>
        </template>
      </Column>
    </DataTable>

    <StudentImportDialog
      ref="importDialog"
      @imported="onImportSuccess"
      @close="onImportClose"
    />
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useToast } from 'primevue/usetoast'
import { DataTable, Column, IconField, InputIcon, InputText, Badge, Button } from 'primevue'
import { Search } from '@primeicons/vue'
import { listStudents, type StudentListItem } from '@/api/students'
import { getCohortColor } from '@/utils/colors'
import StudentImportDialog from './StudentImportDialog.vue'

const toast = useToast()

const students = ref<StudentListItem[]>([])
const totalRecords = ref(0)
const loading = ref(false)
const currentPage = ref(1)
const pageSize = ref(20)
const searchQuery = ref('')
const importDialog = ref<InstanceType<typeof StudentImportDialog>>()

async function fetchStudents(page: number = 1) {
  loading.value = true
  try {
    const response = await listStudents(page, pageSize.value)
    students.value = response.items
    totalRecords.value = response.total
    currentPage.value = page
  } catch (error) {
    toast.add({
      severity: 'error',
      summary: 'Erreur',
      detail: 'Impossible de charger les étudiants',
      life: 3000,
    })
    console.error('Failed to fetch students:', error)
  } finally {
    loading.value = false
  }
}

function onPageChange(event: any) {
  const newPage = Math.floor(event.first / event.rows) + 1
  fetchStudents(newPage)
}

function onSearch() {
  fetchStudents(1)
}

function openImportDialog() {
  importDialog.value?.open()
}

function onImportSuccess() {
  fetchStudents(1)
}

function onImportClose() {
  // Nothing to do on close
}

onMounted(() => {
  fetchStudents()
})
</script>
