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
  total: number
  page: number
  size: number
  total_pages: number
}
