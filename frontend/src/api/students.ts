/**
 * Students API endpoints
 */
import http from './http'
import type { StudentImportDiff, StudentImportMapping } from './types'

export async function importPreview(
  file: File,
  mapping: StudentImportMapping,
  year: number
): Promise<StudentImportDiff> {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('external_id_column', mapping.external_id_column)
  formData.append('first_name_column', mapping.first_name_column)
  formData.append('last_name_column', mapping.last_name_column)
  formData.append('email_column', mapping.email_column)
  formData.append('cohort_column', mapping.cohort_column)
  formData.append('year', String(year))

  const res = await http.post<StudentImportDiff>('/students/import/preview', formData)
  return res.data
}

export async function importApply(
  file: File,
  mapping: StudentImportMapping,
  year: number
): Promise<StudentImportDiff> {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('external_id_column', mapping.external_id_column)
  formData.append('first_name_column', mapping.first_name_column)
  formData.append('last_name_column', mapping.last_name_column)
  formData.append('email_column', mapping.email_column)
  formData.append('cohort_column', mapping.cohort_column)
  formData.append('year', String(year))

  const res = await http.post<StudentImportDiff>('/students/import/apply', formData)
  return res.data
}
