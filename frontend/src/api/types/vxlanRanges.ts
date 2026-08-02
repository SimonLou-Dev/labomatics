/**
 * VXLAN Ranges types
 */

export interface VxlanRangeDTO {
  id: string
  name: string
  base_network: string
  mtu: number
  vni_min: number
  vni_max: number
  exclusions: string[]
  created_at: string
  updated_at: string
}

export interface VxlanRangeCreateDTO {
  name: string
  base_network: string
  mtu: number
  vni_min: number
  vni_max: number
  exclusions?: string[]
}

export interface VxlanRangeUpdateDTO {
  name?: string
  base_network?: string
  mtu?: number
  vni_min?: number
  vni_max?: number
  exclusions?: string[]
}

export interface VxlanAllocationDTO {
  vni: number
  student_login: string
  student_first_name: string
  student_last_name: string
  openwrt_link?: string | null
}
