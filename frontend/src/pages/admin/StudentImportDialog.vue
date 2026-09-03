<template>
  <Dialog v-model:visible="isOpen" :style="{ width: '95vw', height: '95vh' }" modal header="Importer des étudiants" :closable="false">
    <!-- Étape 1: Upload XML -->
    <div v-if="step === 1" class="space-y-4">
      <h2 class="text-lg font-semibold">Étape 1: Importer le fichier CSV</h2>
      <p class="text-sm text-surface-500">Le fichier doit contenir tous les étudiants de toutes les promos.</p>

      <FileUpload
        v-model="uploadedFile"
        name="file"
        :multiple="false"
        accept=".csv"
        :auto="false"
        :show-upload-button="false"
        @select="onFileSelected"
        choose-label="Sélectionner un fichier CSV"
        class="w-full"
      />

      <div v-if="uploadedFile" class="flex items-center gap-3 p-3 bg-surface-800 rounded">
        <i class="pi pi-check-circle text-green-500"></i>
        <span>{{ uploadedFile.name }} ({{ (uploadedFile.size / 1024).toFixed(2) }} KB)</span>
      </div>

      <div v-if="parseError" class="flex items-center gap-3 p-3 bg-red-500/20 border border-red-500 rounded">
        <i class="pi pi-exclamation-circle text-red-500"></i>
        <span>{{ parseError }}</span>
      </div>
    </div>

    <!-- Étape 2: Mapping des colonnes -->
    <div v-if="step === 2" class="space-y-4 h-full overflow-auto">
      <h2 class="text-lg font-semibold">Étape 2: Mapping des colonnes</h2>
      <p class="text-sm text-surface-500">Associez les colonnes du XML aux champs de l'étudiant.</p>

      <div class="grid grid-cols-2 gap-6">
        <div v-for="field in requiredFields" :key="field" class="space-y-2">
          <div class="block text-sm font-medium">{{ field }}</div>
          <Select
            v-model="columnMapping[field]"
            :options="availableColumns"
            option-label="label"
            option-value="value"
            placeholder="Sélectionner une colonne"
            class="w-full"
          />
        </div>
      </div>

      <div class="p-3 bg-surface-800 rounded">
        <p class="text-xs text-surface-400 mb-2">Aperçu des données:</p>
        <table class="text-xs w-full">
          <thead>
            <tr class="border-b border-surface-600">
              <th v-for="col in availableColumns" :key="col.value" class="text-left p-1">{{ col.label }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(row, idx) in previewRows.slice(0, 3)" :key="idx" class="border-b border-surface-700">
              <td v-for="col in availableColumns" :key="col.value" class="p-1">{{ row[col.value] }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Étape 3: Vérification des changements -->
    <div v-if="step === 3" class="space-y-4 h-full overflow-auto">
      <h2 class="text-lg font-semibold">Étape 3: Vérifier les changements</h2>

      <div class="grid grid-cols-4 gap-2 text-sm mb-4">
        <Panel class="p-4 bg-green-500/20 border-2 border-green-500">
          <div class="text-white text-xs font-medium mb-2">Ajoutés</div>
          <div class="text-3xl font-bold text-green-400">{{ diffResult?.added?.length || 0 }}</div>
        </Panel>
        <Panel class="p-4 bg-blue-500/20 border-2 border-blue-500">
          <div class="text-white text-xs font-medium mb-2">Modifiés</div>
          <div class="text-3xl font-bold text-blue-400">{{ diffResult?.modified?.length || 0 }}</div>
        </Panel>
        <Panel class="p-4 bg-red-500/20 border-2 border-red-500">
          <div class="text-white text-xs font-medium mb-2">Supprimés</div>
          <div class="text-3xl font-bold text-red-400">{{ diffResult?.deleted?.length || 0 }}</div>
        </Panel>
        <Panel class="p-4 bg-surface-700 border-2 border-surface-600">
          <div class="text-white text-xs font-medium mb-2">Total</div>
          <div class="text-3xl font-bold text-surface-300">{{ filteredChanges.length }}</div>
        </Panel>
      </div>

      <div class="flex gap-2 mb-4">
        <InputText
          v-model="searchQuery"
          placeholder="Rechercher par nom..."
          class="flex-1"
          size="small"
        />
        <Select
          v-model="filterStatus"
          :options="[
            { label: 'Tous', value: null },
            { label: 'Ajoutés', value: 'added' },
            { label: 'Modifiés', value: 'modified' },
            { label: 'Supprimés', value: 'deleted' }
          ]"
          option-label="label"
          option-value="value"
          placeholder="Filtrer par statut"
          class="w-40"
        />
      </div>

      

      <DataTable
        :value="filteredChanges"
        paginator
        :rows="10"
        :rowsPerPageOptions="[5, 10, 20]"
        dataKey="id"
        class="text-sm"
      >
        <template #empty>Aucun changement</template>
        <Column field="status" header="Statut" style="width: 8%">
          <template #body="{ data }">
            <Badge
              :value="statusLabel(data.status)"
              :severity="statusSeverity(data.status)"
            />
          </template>
        </Column>
        <Column field="id" header="Login" style="width: 12%">
          <template #body="{ data }">
            <span class="font-semibold">{{ data.id }}</span>
          </template>
        </Column>
        <Column field="first_name" header="Prénom" style="width: 15%">
          <template #body="{ data }">
            {{ data.first_name }}
          </template>
        </Column>
        <Column field="last_name" header="Nom" style="width: 15%">
          <template #body="{ data }">
            {{ data.last_name }}
          </template>
        </Column>
        <Column field="email" header="Email" style="width: 20%">
          <template #body="{ data }">
            {{ data.email }}
          </template>
        </Column>
        <Column field="cohort_name" header="Promo" style="width: 15%">
          <template #body="{ data }">
            {{ data.cohort_name }}
          </template>
        </Column>
        <Column field="notes" header="Détails" style="width: 15%">
          <template #body="{ data }">
            <span class="text-xs text-surface-400">{{ data.notes }}</span>
          </template>
        </Column>
      </DataTable>
    </div>

    <!-- Étape 4: Confirmation et import -->
    <div v-if="step === 4" class="space-y-4">
      <h2 class="text-lg font-semibold">Étape 4: Confirmer et importer</h2>
      <p class="text-sm text-surface-500">Vérifiez les informations avant de procéder à l'import.</p>

      <div class="grid grid-cols-4 gap-2 text-sm">
        <Panel class="p-4 bg-green-500/20 border-2 border-green-500">
          <div class="text-white text-xs font-medium mb-2">Ajoutés</div>
          <div class="text-3xl font-bold text-green-400">{{ diffResult?.added?.length || 0 }}</div>
        </Panel>
        <Panel class="p-4 bg-blue-500/20 border-2 border-blue-500">
          <div class="text-white text-xs font-medium mb-2">Modifiés</div>
          <div class="text-3xl font-bold text-blue-400">{{ diffResult?.modified?.length || 0 }}</div>
        </Panel>
        <Panel class="p-4 bg-red-500/20 border-2 border-red-500">
          <div class="text-white text-xs font-medium mb-2">Supprimés</div>
          <div class="text-3xl font-bold text-red-400">{{ diffResult?.deleted?.length || 0 }}</div>
        </Panel>
        <Panel class="p-4 bg-surface-700 border-2 border-surface-600">
          <div class="text-white text-xs font-medium mb-2">Total changements</div>
          <div class="text-3xl font-bold text-surface-300">{{ (diffResult?.added?.length || 0) + (diffResult?.modified?.length || 0) + (diffResult?.deleted?.length || 0) }}</div>
        </Panel>
      </div>
       <div class="flex items-center gap-2">
        <Checkbox v-model="confirmImport" binary inputId="config-checkbox" />
        <Label for="config-checkbox">Je confirme l'import de ces changements</Label>

       </div>

      
    </div>

    <!-- Footer -->
    <template #footer>
      <Button
        v-if="step > 1"
        label="Retour"
        severity="secondary"
        @click="step--"
        :disabled="importing"
      />
      <Button
        v-if="step === 1"
        label="Annuler"
        severity="secondary"
        @click="close"
      />
      <Button
        v-if="step < 4"
        label="Suivant"
        @click="nextStep"
        :disabled="!canProceedToNext || importing"
      />
      <Button
        v-if="step === 4"
        label="Importer"
        severity="success"
        :loading="importing"
        :disabled="!confirmImport"
        @click="performImport"
      />
    </template>
  </Dialog>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useToast } from 'primevue/usetoast'
import {
  Dialog,
  FileUpload,
  DataTable,
  Column,
  Button,
  Select,
  InputText,
  Badge,
  Panel,
  Checkbox,
} from 'primevue'
import * as studentsApi from '@/api/students'

interface ColumnOption {
  label: string
  value: string
}

interface DiffResult {
  added: any[]
  modified: any[]
  deleted: any[]
}

const emit = defineEmits<{
  close: []
  imported: []
}>()

const toast = useToast()
const isOpen = ref(false)
const step = ref(1)

// Étape 1
const uploadedFile = ref<File | null>(null)
const parseError = ref('')

// Étape 2
const requiredFields = ['id', 'first_name', 'last_name', 'email', 'cohort_name']
const columnMapping = ref<Record<string, string>>({})
const availableColumns = ref<ColumnOption[]>([])
const previewRows = ref<any[]>([])

// Étape 3
const diffResult = ref<DiffResult | null>(null)
const searchQuery = ref('')
const filterStatus = ref<string | null>(null)

// Étape 4
const confirmImport = ref(false)
const importing = ref(false)

const canProceedToNext = computed(() => {
  if (step.value === 1) return uploadedFile.value !== null
  if (step.value === 2) return Object.values(columnMapping.value).filter(v => v).length === requiredFields.length
  if (step.value === 3) return diffResult.value !== null
  return true
})

const filteredChanges = computed(() => {
  if (!diffResult.value) return []
  let changes = [
    ...diffResult.value.added.map(d => ({ ...d, status: 'added' })),
    ...diffResult.value.modified.map(d => ({ ...d, status: 'modified' })),
    ...diffResult.value.deleted.map(d => ({ ...d, status: 'deleted' })),
  ]

  if (filterStatus.value) {
    changes = changes.filter(c => c.status === filterStatus.value)
  }

  if (searchQuery.value) {
    const q = searchQuery.value.toLowerCase()
    changes = changes.filter(c =>
      c.login?.toLowerCase().includes(q) ||
      c.first_name?.toLowerCase().includes(q) ||
      c.last_name?.toLowerCase().includes(q)
    )
  }

  return changes
})

function statusLabel(status: string) {
  const labels = { added: 'Ajouté', modified: 'Modifié', deleted: 'Supprimé' }
  return labels[status as keyof typeof labels] || status
}

function statusSeverity(status: string) {
  const severities = { added: 'success', modified: 'info', deleted: 'danger' }
  return severities[status as keyof typeof severities] || 'secondary'
}

async function onFileSelected(event: any) {
  const file = event.files[0]
  if (file) {
    try {
      parseError.value = ''
      const text = await file.text()

      // Parser CSV simple
      const lines = text.split('\n').filter((l: string) => l.trim())
      if (lines.length < 2) {
        parseError.value = 'Le fichier doit contenir au moins un en-tête et une ligne de données'
        uploadedFile.value = null
        return
      }

      // Première ligne = en-tête
      const headers = lines[0].split(',').map((h: string) => h.trim())
      const columns = new Set(headers)
      const data: any[] = []

      // Parcourir les lignes de données
      for (let i = 1; i < Math.min(lines.length, 100); i++) {
        const values = lines[i].split(',').map((v: string) => v.trim())
        const rowData: Record<string, string> = {}
        headers.forEach((header: string, idx: number) => {
          rowData[header] = values[idx] || ''
        })
        if (rowData[headers[0]]) {
          // S'assurer qu'il y a au moins une valeur
          data.push(rowData)
        }
      }

      availableColumns.value = Array.from(columns).map((c) => ({ label: String(c), value: String(c) }))
      previewRows.value = data
      uploadedFile.value = file
    } catch (error) {
      parseError.value = `Erreur lors de la lecture du fichier: ${(error as Error).message}`
      uploadedFile.value = null
    }
  }
}

async function nextStep() {
  if (step.value === 2) {
    // Appeler l'API pour faire le diff
    try {
      const file = uploadedFile.value
      if (!file) return

      const formData = new FormData()
      formData.append('file', file)
      for (const [field, col] of Object.entries(columnMapping.value)) {
        if (col) {
          formData.append(field, col)
        }
      }

      diffResult.value = await studentsApi.previewStudentImport(formData)
    } catch (error) {
      toast.add({
        severity: 'error',
        summary: 'Erreur',
        detail: `Erreur lors de l'analyse: ${(error as Error).message}`,
        life: 3000,
      })
      return
    }
  }
  step.value++
}

async function performImport() {
  if (!uploadedFile.value) return
  importing.value = true

  try {
    const formData = new FormData()
    formData.append('file', uploadedFile.value)
    for (const [field, col] of Object.entries(columnMapping.value)) {
      if (col) {
        formData.append(field, col)
      }
    }

    await studentsApi.applyStudentImport(formData)
    toast.add({
      severity: 'success',
      summary: 'Succès',
      detail: 'Étudiants importés avec succès',
      life: 3000,
    })
    emit('imported')
    close()
  } catch (error) {
    toast.add({
      severity: 'error',
      summary: 'Erreur',
      detail: `Erreur lors de l'import: ${(error as Error).message}`,
      life: 3000,
    })
  } finally {
    importing.value = false
  }
}

function close() {
  isOpen.value = false
  step.value = 1
  uploadedFile.value = null
  parseError.value = ''
  searchQuery.value = ''
  filterStatus.value = null
  confirmImport.value = false
  columnMapping.value = {}
  diffResult.value = null
  emit('close')
}

function open() {
  isOpen.value = true
}

defineExpose({ open, close })
</script>
