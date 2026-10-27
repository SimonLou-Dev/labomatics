<template>
  <div class="min-h-screen bg-surface-900 dark:bg-surface-50 p-6">
    <div class="mb-6 flex justify-between items-center">
      <h1 class="text-3xl font-bold">
        Professeurs
      </h1>
      <Button
        label="Ajouter un professeur"
        icon="pi pi-plus"
        severity="success"
        @click="openCreateDialog"
      />
    </div>

    <div class="mb-4 flex justify-end">
      <IconField>
        <InputIcon>
          <Search />
        </InputIcon>
        <InputText
          v-model="searchQuery"
          type="text"
          placeholder="Rechercher par nom / prénom / email / login"
        />
      </IconField>
    </div>

    <div class="overflow-x-auto">
      <DataTable
        v-model:rows="pageSize"
        :value="teachers"
        data-key="id"
        :rows-per-page-options="[5, 10, 20, 50]"
        :total-records="totalRecords"
        :loading="loading"
        :lazy="true"
        paginator
        scrollable
        scroll-height="calc(100vh - 300px)"
        @page="onPageChange"
      >
        <template #empty>
          Aucun professeur trouvé
        </template>

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
          style="width: 18%"
        >
          <template #body="{ data }">
            <span class="font-semibold">{{ data.first_name }} {{ data.last_name }}</span>
          </template>
        </Column>

        <Column
          field="email"
          header="Email"
          style="width: 20%"
        >
          <template #body="{ data }">
            <span class="text-sm">{{ data.email }}</span>
          </template>
        </Column>

        <Column
          field="cohort_names"
          header="Classes assignées"
          style="width: 25%"
        >
          <template #body="{ data }">
            <div
              v-if="data.cohort_names.length > 0"
              class="flex flex-wrap gap-1"
            >
              <Badge
                v-for="name in data.cohort_names"
                :key="name"
                :value="name"
                :severity="getCohortColor(name)"
              />
            </div>
            <span
              v-else
              class="text-surface-400"
            >Aucune</span>
          </template>
        </Column>

        <Column
          field="is_active"
          header="Statut"
          style="width: 10%"
        >
          <template #body="{ data }">
            <Badge
              :value="data.is_active ? 'Actif' : 'Inactif'"
              :severity="data.is_active ? 'success' : 'secondary'"
            />
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
                v-tooltip="'Éditer'"
                icon="pi pi-pencil"
                severity="secondary"
                size="small"
                @click="openEditDialog(data)"
              />
              <Button
                v-tooltip="'Désactiver'"
                icon="pi pi-trash"
                severity="danger"
                size="small"
                :loading="deletingId === data.id"
                @click="confirmDelete(data)"
              />
            </div>
          </template>
        </Column>
      </DataTable>
    </div>

    <!-- Create/Edit Modal -->
    <Dialog
      v-model:visible="showFormDialog"
      :header="editingTeacher ? 'Modifier le professeur' : 'Ajouter un professeur'"
      modal
      :style="{ width: '100vw', maxWidth: '500px' }"
    >
      <div class="space-y-4">
        <div>
          <label class="block text-sm font-medium mb-2">Prénom</label>
          <InputText
            v-model="formData.first_name"
            class="w-full"
          />
        </div>
        <div>
          <label class="block text-sm font-medium mb-2">Nom</label>
          <InputText
            v-model="formData.last_name"
            class="w-full"
          />
        </div>
        <div>
          <label class="block text-sm font-medium mb-2">Email</label>
          <InputText
            v-model="formData.email"
            type="email"
            class="w-full"
          />
        </div>
        <div>
          <label class="block text-sm font-medium mb-2">Classes assignées cette année</label>
          <MultiSelect
            v-model="formData.cohort_ids"
            :options="allCohorts"
            option-label="name"
            option-value="id"
            placeholder="Sélectionner les classes"
            display="chip"
            class="w-full"
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
          :label="editingTeacher ? 'Mettre à jour' : 'Créer'"
          :loading="formLoading"
          @click="saveTeacher"
        />
      </template>
    </Dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import { useToast } from 'primevue/usetoast'
import { useConfirm } from 'primevue/useconfirm'
import {
  DataTable,
  Column,
  Button,
  Dialog,
  Badge,
  InputText,
  MultiSelect,
  IconField,
  InputIcon,
} from 'primevue'
import { Search } from '@primeicons/vue'
import type { DataTableSimplePageEvent } from '@/api/types'
import type { CohortDTO } from '@/api/types/cohorts'
import type { TeacherCreatePayload, TeacherListItem } from '@/api/types/teacher'
import * as teachersApi from '@/api/teachers'
import * as cohortsApi from '@/api/cohorts'
import { getCohortColor } from '@/utils/colors'

const toast = useToast()
const confirm = useConfirm()

const teachers = ref<TeacherListItem[]>([])
const allCohorts = ref<CohortDTO[]>([])
const totalRecords = ref(0)
const loading = ref(false)
const currentPage = ref(1)
const pageSize = ref(20)
const searchQuery = ref('')
const deletingId = ref<string | null>(null)

const showFormDialog = ref(false)
const editingTeacher = ref<TeacherListItem | null>(null)
const formLoading = ref(false)
const formData = ref<TeacherCreatePayload>({
  first_name: '',
  last_name: '',
  email: '',
  cohort_ids: [],
})

async function fetchTeachers(page: number = 1) {
  loading.value = true
  try {
    const response = await teachersApi.listTeachers(page, pageSize.value, searchQuery.value || undefined)
    teachers.value = response.items
    totalRecords.value = response.total_count
    currentPage.value = page
  } catch (err) {
    toast.add({ severity: 'error', summary: 'Erreur', detail: 'Impossible de charger les professeurs', life: 3000 })
    console.error('Failed to fetch teachers:', err)
  } finally {
    loading.value = false
  }
}

async function loadAllCohorts() {
  try {
    const response = await cohortsApi.listCohorts(1, 100)
    allCohorts.value = response.items
  } catch (err) {
    console.error('Failed to load cohorts:', err)
  }
}

function onPageChange(event: DataTableSimplePageEvent) {
  fetchTeachers(event.page + 1)
}

function openCreateDialog() {
  editingTeacher.value = null
  formData.value = { first_name: '', last_name: '', email: '', cohort_ids: [] }
  showFormDialog.value = true
}

function openEditDialog(teacher: TeacherListItem) {
  editingTeacher.value = teacher
  formData.value = {
    first_name: teacher.first_name,
    last_name: teacher.last_name,
    email: teacher.email,
    cohort_ids: allCohorts.value
      .filter((c) => teacher.cohort_names.includes(c.name))
      .map((c) => c.id),
  }
  showFormDialog.value = true
}

async function saveTeacher() {
  formLoading.value = true
  try {
    if (editingTeacher.value) {
      await teachersApi.updateTeacher(editingTeacher.value.id, formData.value)
      toast.add({ severity: 'success', summary: 'Succès', detail: 'Professeur mis à jour', life: 3000 })
    } else {
      await teachersApi.createTeacher(formData.value)
      toast.add({ severity: 'success', summary: 'Succès', detail: 'Professeur créé', life: 3000 })
    }
    showFormDialog.value = false
    await fetchTeachers(currentPage.value)
  } catch (err) {
    toast.add({
      severity: 'error',
      summary: 'Erreur',
      detail: 'Impossible de sauvegarder le professeur',
      life: 3000,
    })
    console.error('Failed to save teacher:', err)
  } finally {
    formLoading.value = false
  }
}

function confirmDelete(teacher: TeacherListItem) {
  confirm.require({
    message: `Êtes-vous sûr de vouloir désactiver ${teacher.first_name} ${teacher.last_name} ?`,
    header: 'Confirmation',
    icon: 'pi pi-exclamation-triangle',
    acceptClass: 'p-button-danger',
    accept: () => deleteTeacher(teacher),
  })
}

async function deleteTeacher(teacher: TeacherListItem) {
  deletingId.value = teacher.id
  try {
    await teachersApi.deleteTeacher(teacher.id)
    toast.add({ severity: 'success', summary: 'Succès', detail: 'Professeur désactivé', life: 3000 })
    await fetchTeachers(currentPage.value)
  } catch (err) {
    toast.add({ severity: 'error', summary: 'Erreur', detail: 'Impossible de désactiver le professeur', life: 3000 })
    console.error('Failed to delete teacher:', err)
  } finally {
    deletingId.value = null
  }
}

onMounted(() => {
  fetchTeachers()
  loadAllCohorts()

  watch([pageSize, searchQuery], () => {
    fetchTeachers(1)
  })
})
</script>
