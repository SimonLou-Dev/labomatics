<template>
  <div class="min-h-screen bg-surface-900 dark:bg-surface-50 p-6">
    <div class="mb-6 flex justify-between items-center">
      <h1 class="text-3xl font-bold">
        Mes élèves
      </h1>
      <Button
        label="Créer mon lab"
        icon="pi pi-plus"
        severity="success"
        @click="router.push('/lab')"
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
          placeholder="Rechercher par nom / prénom / email"
        />
      </IconField>
    </div>

    <div class="overflow-x-auto">
      <DataTable
        v-model:rows="pageSize"
        :value="students"
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
          Aucun élève trouvé — vérifiez que des classes vous sont assignées.
        </template>

        <Column
          field="first_name"
          header="Nom"
          style="width: 20%"
        >
          <template #body="{ data }">
            <span class="font-semibold">{{ data.first_name }} {{ data.last_name }}</span>
          </template>
        </Column>

        <Column
          field="email"
          header="Email"
          style="width: 22%"
        >
          <template #body="{ data }">
            <span class="text-sm">{{ data.email }}</span>
          </template>
        </Column>

        <Column
          field="cohort_name"
          header="Classe"
          style="width: 15%"
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
          style="width: 15%"
        >
          <template #body="{ data }">
            <span
              v-if="data.wan_ip"
              class="font-mono text-sm"
            >{{ data.wan_ip }}</span>
            <span
              v-else
              class="text-surface-400"
            >—</span>
          </template>
        </Column>
      </DataTable>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useToast } from 'primevue/usetoast'
import { DataTable, Column, Badge, IconField, InputIcon, InputText, Button } from 'primevue'
import { Search } from '@primeicons/vue'
import type { StudentListItem } from '@/api/types/students'
import type { DataTableSimplePageEvent } from '@/api/types'
import * as teachersApi from '@/api/teachers'
import { getCohortColor } from '@/utils/colors'

const router = useRouter()
const toast = useToast()

const students = ref<StudentListItem[]>([])
const totalRecords = ref(0)
const loading = ref(false)
const currentPage = ref(1)
const pageSize = ref(20)
const searchQuery = ref('')

async function fetchStudents(page: number = 1) {
  loading.value = true
  try {
    const response = await teachersApi.listMyStudents(page, pageSize.value, searchQuery.value || undefined)
    students.value = response.items
    totalRecords.value = response.total_count
    currentPage.value = page
  } catch (err) {
    toast.add({ severity: 'error', summary: 'Erreur', detail: 'Impossible de charger les élèves', life: 3000 })
    console.error('Failed to fetch students for teacher:', err)
  } finally {
    loading.value = false
  }
}

function onPageChange(event: DataTableSimplePageEvent) {
  fetchStudents(event.page + 1)
}

onMounted(() => {
  fetchStudents()

  watch([pageSize, searchQuery], () => {
    fetchStudents(1)
  })
})
</script>
