import { defineStore } from 'pinia'
import { ref } from 'vue'
import { importPreview, importApply } from '@/api/students'
import type { StudentImportDiff, StudentImportMapping } from '@/api'

export const useStudentsStore = defineStore('students', () => {
  const loading = ref(false)
  const error = ref<string | null>(null)

  const preview = (
    file: File,
    mapping: StudentImportMapping,
    year: number
  ) => {
    loading.value = true
    error.value = null

    return importPreview(file, mapping, year)
      .then((data) => {
        error.value = null
        return data
      })
      .catch((err) => {
        error.value = err instanceof Error ? err.message : 'Import preview failed'
        throw err
      })
      .finally(() => {
        loading.value = false
      })
  }

  const apply = (
    file: File,
    mapping: StudentImportMapping,
    year: number
  ) => {
    loading.value = true
    error.value = null

    return importApply(file, mapping, year)
      .then((data) => {
        error.value = null
        return data
      })
      .catch((err) => {
        error.value = err instanceof Error ? err.message : 'Import apply failed'
        throw err
      })
      .finally(() => {
        loading.value = false
      })
  }

  return {
    loading,
    error,
    preview,
    apply,
  }
})
