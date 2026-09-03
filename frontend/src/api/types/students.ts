/**
 * Students types
 */

export interface StudentListItem {
  id: string
  login: string
  email: string
  first_name: string
  last_name: string
  cohort_name: string
  wan_ip: string | null
  vxlan_tag: number | null
}

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

export interface StudentImportItemXML {
  login: string
  first_name: string
  last_name: string
  email: string
  cohort_name?: string
  notes?: string
}

export interface StudentImportDiffXML {
  added: StudentImportItemXML[]
  modified: StudentImportItemXML[]
  deleted: StudentImportItemXML[]
  errors: string[]
}

export interface StudentDetailDTO {
  id: string
  login: string
  email: string
  first_name: string
  last_name: string
  cohort_name: string
  created_at: string
}

export interface LabVmDTO {
  id: string
  name: string
  cluster_name: string
  state: string
  cores: number
  memory: number
  disk: number
  created_at: string
  notes: string | null
}

export interface LabAllocationDTO {
  type: 'wan' | 'vxlan'
  value: string | number
}

export interface LabDataDTO {
  student: StudentDetailDTO
  vms: LabVmDTO[]
  wan_ip: string | null
  vxlan_tag: number | null
  openwrt_link: string | null
}
