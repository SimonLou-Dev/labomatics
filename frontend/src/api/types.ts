/**
 * API Response Types
 */

export type { LabDataDTO } from './types/students'

export interface JobDTO {
  jobId: string
}

export interface StudentImportDiff {
  created: number
  updated: number
  deleted: number
}

export interface StudentImportDiffXML {
  added: StudentImportChange[]
  modified: StudentImportChange[]
  deleted: StudentImportChange[]
}

export interface StudentImportMapping {
  external_id_column: string
  last_name_column: string
  first_name_column: string
  email_column: string
  cohort_column: string
}

export interface IpRangeDTO {
  id: string
  name: string
  network: string
  gateway: string
  exclusions: string[] | null
  total_ips: number
  used_count: number
  free_count: number
  utilization_percent: number
}

export interface IpRangeCreateDTO {
  name: string
  network: string
  gateway: string
  exclusions?: string[]
}

export type IpRangeUpdateDTO = IpRangeCreateDTO

export interface IpAllocationDTO {
  ip_address: string
  student_login: string | null
  student_first_name: string | null
  student_last_name: string | null
  wan_ip_taken_by: string | null
  is_taken: boolean
  openwrt_link?: string | null
}

export interface VxlanRangeDTO {
  id: string
  name: string
  vni_min: number
  vni_max: number
  base_network: string
  mtu: number
  exclusions: string[] | null
  total_vnis: number
  used_count: number
  free_count: number
  utilization_percent: number
}

export interface VxlanRangeCreateDTO {
  name: string
  base_network: string
  mtu?: number
  vni_min?: number
  vni_max?: number
  exclusions?: string[]
}

export type VxlanRangeUpdateDTO = VxlanRangeCreateDTO

export interface VxlanAllocationDTO {
  vni: number | null
  student_login: string | null
  student_first_name: string | null
  student_last_name: string | null
  vxlan_tag_taken_by: string | null
  is_taken: boolean
}

export interface MeDTO {
  subject: string
  username: string
  email: string
  roles: string[]
}

export interface AuthResponse {
  access_token: string
  token_type: string
  logout_url?: string
}

export interface ClusterDTO {
  id: string
  name: string
  url: string
  default_storage: string
  sdn_zone: string
  wan_bridge?: string
  ip_ranges?: IpRangeDTO[]
  vxlan_ranges?: VxlanRangeDTO[]
}

export interface ClusterCreateDTO {
  name: string
  url: string
  default_storage: string
  sdn_zone: string
  wan_bridge?: string
}

export type ClusterUpdateDTO = ClusterCreateDTO

export interface ClusterCredentialWriteDTO {
  token_id: string
  token_secret: string
}

export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  per_page: number
}

export interface StudentListItem {
  id: string
  external_id: number
  last_name: string
  first_name: string
  email: string
  login: string
  is_active: boolean
  cohort_name?: string
}

export interface ImportStudentRow {
  [key: string]: string
}

export interface StudentImportChange {
  id?: string
  login?: string
  first_name?: string
  last_name?: string
  email?: string
  cohort_name?: string
  notes?: string
  status?: 'added' | 'modified' | 'deleted'
}

export interface StudentImportDiffResponse {
  added: StudentImportChange[]
  modified: StudentImportChange[]
  deleted: StudentImportChange[]
}

export interface StudentDetailDTO extends StudentListItem {
  keycloak_user_id?: string
  proxmox_userid?: string
  left_at?: string
}

export interface StudentDTO {
  id: string
  login: string
  first_name: string
  last_name: string
  email: string
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
  notes?: string | null
}

// UI Events and Types
export interface DataTablePageChangeEvent {
  first: number
  rows: number
}

export interface DataTableSimplePageEvent {
  page: number
}

export interface FileSelectEvent {
  files: File[]
}

export interface MenuItem {
  label: string
  icon?: unknown
  command?: () => void
  items?: MenuItem[]
}

export interface MenuItemGroup {
  label: string
  items: MenuItem[]
}
