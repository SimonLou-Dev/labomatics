/**
 * VXLAN Ranges types
 */

import type { StudentSimpleDTO } from './ipRanges'

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
  mtu: number
  vni_min: number
  vni_max: number
  exclusions?: string[] | null
}

export interface VxlanRangeUpdateDTO {
  name?: string
  base_network?: string
  mtu?: number
  vni_min?: number
  vni_max?: number
  exclusions?: string[] | null
}

export interface VxlanAllocationDTO {
  vni: number | null
  student: StudentSimpleDTO | null
  is_taken: boolean
}

export interface VxlanAllocationPaginatedDTO {
  items: VxlanAllocationDTO[]
  total: number
  page: number
  per_page: number
  total_pages: number
}
