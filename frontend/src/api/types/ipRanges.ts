/**
 * IP Ranges types
 */

export interface IpRangeDTO {
  id: string
  name: string
  network: string
  gateway: string
  exclusions: string[]
  created_at: string
  updated_at: string
}

export interface IpRangeCreateDTO {
  name: string
  network: string
  gateway: string
  exclusions?: string[]
}

export interface IpRangeUpdateDTO {
  name?: string
  network?: string
  gateway?: string
  exclusions?: string[]
}

export interface IpAllocationDTO {
  ip_address: string
  student_login: string
  student_first_name: string
  student_last_name: string
  openwrt_link?: string | null
}
