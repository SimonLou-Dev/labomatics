/**
 * Common API types
 */

export interface ApiError {
  detail: string
}

export interface PaginatedResponse<T> {
  items: T[]
  total_count: number
  page: number
  size: number
  total_pages: number
}
