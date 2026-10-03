export interface ClusterRefDTO {
  id: string
  name: string
  is_default: boolean
}

export interface CohortDTO {
  id: string
  name: string
  year: number
  is_active: boolean
  clusters: ClusterRefDTO[]
}

export interface CohortListResponseDTO {
  items: CohortDTO[]
  total_count: number
  page: number
  per_page: number
  total_pages: number
}
