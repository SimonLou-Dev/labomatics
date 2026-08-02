/**
 * IP Ranges types
 */

export interface IpRangeDTO {
  id: string
  name: string
  network: string
  gateway: string
  exclusions: string[]
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
