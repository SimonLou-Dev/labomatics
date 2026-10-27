/**
 * Teachers API endpoints (#58)
 */
import http from './http'
import type { PaginatedResponse } from './types/common'
import type { StudentListItem } from './types/students'
import type { TeacherCreatePayload, TeacherListItem, TeacherUpdatePayload } from './types/teacher'

export async function listTeachers(
  page: number,
  size: number,
  search?: string
): Promise<PaginatedResponse<TeacherListItem>> {
  const res = await http.get<PaginatedResponse<TeacherListItem>>('/teachers', {
    params: { page, size, ...(search && { search }) },
  })
  return res.data
}

export async function createTeacher(payload: TeacherCreatePayload): Promise<TeacherListItem> {
  const res = await http.post<TeacherListItem>('/teachers', payload)
  return res.data
}

export async function updateTeacher(teacherId: string, payload: TeacherUpdatePayload): Promise<TeacherListItem> {
  const res = await http.patch<TeacherListItem>(`/teachers/${teacherId}`, payload)
  return res.data
}

export async function deleteTeacher(teacherId: string): Promise<void> {
  await http.delete(`/teachers/${teacherId}`)
}

export async function listMyStudents(
  page: number,
  size: number,
  search?: string
): Promise<PaginatedResponse<StudentListItem>> {
  const res = await http.get<PaginatedResponse<StudentListItem>>('/teachers/me/students', {
    params: { page, size, ...(search && { search }) },
  })
  return res.data
}
