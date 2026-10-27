export interface ClusterRefDTO {
  id: string
  name: string
  is_default: boolean
  has_active_lab: boolean
}

export interface CohortDTO {
  id: string
  name: string
  year: number
  school_year: string
  is_active: boolean
  start_date: string | null
  end_date: string | null
  clusters: ClusterRefDTO[]
}

export interface CohortUpdatePayload {
  start_date?: string | null
  end_date?: string | null
}

export interface CohortListResponseDTO {
  items: CohortDTO[]
  total_count: number
  page: number
  per_page: number
  total_pages: number
}
