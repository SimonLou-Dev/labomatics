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
  keycloak_login?: string | null
}

export type TeacherUpdatePayload = TeacherCreatePayload

export interface KeycloakUserLookup {
  login: string
  email: string
  first_name: string
  last_name: string
}
