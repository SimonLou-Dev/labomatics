/**
 * IP Ranges types
 */

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
  exclusions?: string[] | null
}

export interface IpRangeUpdateDTO {
  name?: string
  network?: string
  gateway?: string
  exclusions?: string[] | null
}

export interface StudentSimpleDTO {
  id: string
  login: string
  first_name: string
  last_name: string
}

export interface IpAllocationDTO {
  ip_address: string | null
  student: StudentSimpleDTO | null
  is_taken: boolean
}

export interface IpAllocationPaginatedDTO {
  items: IpAllocationDTO[]
  total: number
  page: number
  per_page: number
  total_pages: number
}
