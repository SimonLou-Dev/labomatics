/**
 * Students types
 */

export interface StudentImportRow {
  external_id: number
  first_name: string
  last_name: string
  email: string
  cohort: string
}

export interface StudentImportMapping {
  external_id_column: string
  first_name_column: string
  last_name_column: string
  email_column: string
  cohort_column: string
}

export interface StudentImportDiff {
  created: StudentImportCreated[]
  updated: StudentImportUpdated[]
  removed: StudentImportRemoved[]
  errors: StudentImportError[]
}

export interface StudentImportCreated {
  external_id: number
  login: string
  email: string
  cohort_name: string
}

export interface StudentImportUpdated {
  external_id: number
  changes: Record<string, string>
}

export interface StudentImportRemoved {
  external_id: number
  login: string
}

export interface StudentImportError {
  row_index: number
  external_id?: string
  reason: string
}
