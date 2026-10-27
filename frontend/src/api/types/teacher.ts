/**
 * Teacher types (#58)
 */

export interface TeacherListItem {
  id: string
  login: string
  email: string
  first_name: string
  last_name: string
  cohort_names: string[]
  is_active: boolean
}

export interface TeacherCreatePayload {
  first_name: string
  last_name: string
  email: string
  cohort_ids: string[]
}

export type TeacherUpdatePayload = TeacherCreatePayload
