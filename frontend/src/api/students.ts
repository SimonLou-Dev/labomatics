/**
 * Students API endpoints
 */
import http from './http'
import type {
  StudentImportDiff,
  StudentImportMapping,
  StudentListItem,
  StudentDetailDTO,
  LabDataDTO,
  StudentImportDiffXML,
} from './types'
import type { PaginatedResponse } from './types'

export type { StudentListItem, StudentImportDiffXML } from './types'

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

export async function listStudents(
  page: number,
  perPage: number,
  search?: string,
  cohort?: string
): Promise<PaginatedResponse<StudentListItem>> {
  const res = await http.get<PaginatedResponse<StudentListItem>>('/students', {
    params: {
      page,
      size: perPage,
      ...(search && { search }),
      ...(cohort && { cohort }),
    },
  })
  return res.data
}

export async function getStudentDetail(studentId: string): Promise<StudentDetailDTO> {
  const res = await http.get<StudentDetailDTO>(`/students/${studentId}`)
  return res.data
}

export async function getLabData(studentId: string): Promise<LabDataDTO> {
  const res = await http.get<LabDataDTO>(`/students/${studentId}/lab`)
  return res.data
}

export async function getLabDataForMe(): Promise<LabDataDTO> {
  const res = await http.get<LabDataDTO>('/me/lab')
  return res.data
}

export async function previewStudentImport(formData: FormData): Promise<StudentImportDiffXML> {
  const res = await http.post<StudentImportDiffXML>('/students/import-csv/preview', formData)
  return res.data
}

export async function applyStudentImport(formData: FormData): Promise<StudentImportDiffXML> {
  const res = await http.post<StudentImportDiffXML>('/students/import-csv/apply', formData)
  return res.data
}
