/**
 * API Response Types
 */

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
  exclusions: string[]
  utilization_percent?: number
}

export interface IpRangeCreateDTO {
  name: string
  network: string
  gateway: string
  exclusions?: string[]
}

export type IpRangeUpdateDTO = IpRangeCreateDTO

export interface IpAllocationDTO {
  id: string
  ipRangeId: string
  allocatedIp: string
}

export interface VxlanRangeDTO {
  id: string
  name: string
  base_network: string
  mtu: number
  vni_min: number
  vni_max: number
  exclusions: string[]
  utilization_percent?: number
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
  id: string
  vxlanRangeId: string
  allocatedVni: number
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

export interface LabStudentInfo {
  id: string
  first_name: string
  last_name: string
  login: string
  email: string
  cohort_name?: string
  created_at: string
}

export interface LabVMInfo {
  id: string
  name: string
  cluster_name: string
  state: string
  cores: number
  memory: number
  disk: number
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

export interface LabDataDTO {
  id: string
  status: string
  created_at: string
  cluster_name?: string
  wan_ip?: string
  vxlan_tag?: number | null
  subnet?: string
  vm_count?: number
  openwrt_url?: string
  student_name?: string
  student_email?: string
  student_cohort?: string
  student?: LabStudentInfo
  vms?: LabVMInfo[]
}
