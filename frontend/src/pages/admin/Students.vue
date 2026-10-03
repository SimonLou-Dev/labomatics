<template>
  <div class="min-h-screen bg-surface-900 dark:bg-surface-50 p-6">
    <div class="mb-6 flex justify-between items-center">
      <h1 class="text-3xl font-bold">
        Étudiants
      </h1>
      <Button
        label="Importer CSV"
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
          type="text"
          placeholder="Rechercher par nom / prénom / email / IP"
        />
      </IconField>
    </div>

    <DataTable
      :value="students"
      data-key="id"
      :rows="pageSize"
      :rows-per-page-options="[5, 10, 20, 50]"
      :total-records="totalRecords"
      :loading="loading"
      :lazy="true"
      paginator
      sort-field="last_name"
      :sort-order="1"
      :first="currentPage"
      @page="onPageChange"
    >
      <template #empty>
        Aucun étudiant trouvé
      </template>

      <Column
        field="id"
        header="#"
        style="width: 8%"
      >
        <template #body="{ data }">
          <span class="font-semibold text-sm">{{ data.id.slice(0, 8) }}</span>
        </template>
      </Column>

      <Column
        field="login"
        header="Login"
        style="width: 12%"
      >
        <template #body="{ data }">
          <span class="font-semibold">{{ data.login }}</span>
        </template>
      </Column>

      <Column
        field="first_name"
        header="Nom"
        style="width: 15%"
      >
        <template #body="{ data }">
          <span class="font-semibold">{{ data.first_name }} {{ data.last_name }}</span>
        </template>
      </Column>

      <Column
        field="email"
        header="Email"
        style="width: 18%"
      >
        <template #body="{ data }">
          <span class="font-semibold text-sm">{{ data.email }}</span>
        </template>
      </Column>

      <Column
        field="cohort_name"
        header="Promo"
        style="width: 12%"
      >
        <template #body="{ data }">
          <Badge
            :value="data.cohort_name"
            :severity="getCohortColor(data.cohort_name)"
          />
        </template>
      </Column>

      <Column
        field="wan_ip"
        header="IP WAN"
        style="width: 12%"
      >
        <template #body="{ data }">
          <span
            v-if="data.wan_ip"
            class="font-mono text-sm"
          >
            {{ data.wan_ip }}
          </span>
          <span
            v-else
            class="text-surface-400"
          >—</span>
        </template>
      </Column>

      <Column
        field="vxlan_tag"
        header="VNI"
        style="width: 8%"
      >
        <template #body="{ data }">
          <span
            v-if="data.vxlan_tag"
            class="font-mono font-semibold"
          >
            {{ data.vxlan_tag }}
          </span>
          <span
            v-else
            class="text-surface-400"
          >—</span>
        </template>
      </Column>

      <Column
        field="actions"
        header="Actions"
        style="width: 15%"
      >
        <template #body="{ data }">
          <div class="flex gap-2">
            <Button
              v-tooltip="data.wan_ip ? 'Recréer le lab' : 'Déployer le lab'"
              icon="pi pi-replay"
              severity="secondary"
              size="small"
              :loading="deployingStudentId === data.id"
              @click="confirmForceCreateLab(data)"
            />
            <Button
              v-tooltip="'Supprimer'"
              icon="pi pi-trash"
              severity="danger"
              size="small"
              :loading="deletingStudentId === data.id"
              @click="confirmDeleteStudent(data)"
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
import { onMounted, ref, watch } from 'vue'
import { useToast } from 'primevue/usetoast'
import { useConfirm } from 'primevue/useconfirm'
import {
  DataTable,
  Column,
  IconField,
  InputIcon,
  InputText,
  Badge,
  Button,
  Select,
} from 'primevue'
import { Search } from '@primeicons/vue'
import { listStudents, forceCreateStudentLab, deleteStudent as deleteStudentApi, type StudentListItem } from '@/api/students'
import type { DataTablePageChangeEvent } from '@/api/types'
import { getCohortColor } from '@/utils/colors'
import StudentImportDialog from './StudentImportDialog.vue'

const toast = useToast()
const confirm = useConfirm()

const students = ref<StudentListItem[]>([])
const totalRecords = ref(0)
const loading = ref(false)
const currentPage = ref(0)
const pageSize = ref(10)
const searchQuery = ref<string>('')
const importDialog = ref<InstanceType<typeof StudentImportDialog>>()
const deployingStudentId = ref<string | null>(null)
const deletingStudentId = ref<string | null>(null)

async function fetchStudents(page: number = 1) {
  loading.value = true
  try {
    const response = await listStudents(
      page,
      pageSize.value,
      searchQuery.value || undefined,
      undefined
    )
    students.value = response.items
    totalRecords.value = response.total_count
    if (page === 1) {
      currentPage.value = 0
    }
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

function onPageChange(event: DataTablePageChangeEvent) {
  currentPage.value = event.first
  const pageNumber = Math.floor(event.first / event.rows) + 1
  fetchStudents(pageNumber)
}

onMounted(() => {
  fetchStudents()

  // Watch sur la recherche
  watch(
    () => searchQuery.value,
    () => {
      fetchStudents(1)
    }
  )

  // Watch sur le changement de page size
  watch(
    () => pageSize.value,
    () => {
      fetchStudents(1)
    }
  )
})

function openImportDialog() {
  importDialog.value?.open()
}

function onImportSuccess() {
  fetchStudents(1)
}

function onImportClose() {
  // Nothing to do on close
}

function confirmForceCreateLab(student: StudentListItem) {
  confirm.require({
    message: `Êtes-vous sûr de vouloir ${
      student.wan_ip ? 'recréer' : 'créer'
    } le lab pour ${student.first_name} ${student.last_name} ?`,
    header: 'Confirmation',
    icon: 'pi pi-exclamation-triangle',
    accept: () => forceCreateLab(student),
  })
}

async function forceCreateLab(student: StudentListItem) {
  deployingStudentId.value = student.id
  try {
    await forceCreateStudentLab(student.id)
    toast.add({
      severity: 'success',
      summary: 'Succès',
      detail: `Lab de ${student.first_name} ${student.last_name} en cours de création`,
      life: 3000,
    })
    fetchStudents(currentPage.value)
  } catch (error) {
    toast.add({
      severity: 'error',
      summary: 'Erreur',
      detail: 'Impossible de créer le lab',
      life: 3000,
    })
    console.error('Failed to create lab:', error)
  } finally {
    deployingStudentId.value = null
  }
}

function confirmDeleteStudent(student: StudentListItem) {
  confirm.require({
    message: `Êtes-vous sûr de vouloir supprimer ${student.first_name} ${student.last_name} ? Cette action ne peut pas être annulée.`,
    header: 'Confirmation de suppression',
    icon: 'pi pi-exclamation-triangle',
    acceptClass: 'p-button-danger',
    accept: () => deleteStudent(student),
  })
}

async function deleteStudent(student: StudentListItem) {
  deletingStudentId.value = student.id
  try {
    await deleteStudentApi(student.id)
    toast.add({
      severity: 'success',
      summary: 'Supprimé',
      detail: `${student.first_name} ${student.last_name} a été supprimé`,
      life: 3000,
    })
    fetchStudents(currentPage.value)
  } catch (error) {
    toast.add({
      severity: 'error',
      summary: 'Erreur',
      detail: 'Impossible de supprimer l\'étudiant',
      life: 3000,
    })
    console.error('Failed to delete student:', error)
  } finally {
    deletingStudentId.value = null
  }
}
</script>
