const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api'

export interface StudentListItem {
  id: string
  login: string
  email: string
  first_name: string
  last_name: string
  cohort_name: string
  wan_ip: string | null
  vxlan_tag: number | null
}

export interface StudentListResponse {
  items: StudentListItem[]
  total_count: number
  page: number
  size: number
  total_pages: number
}

export async function getStudents(
  page: number = 1,
  size: number = 20,
  token?: string
): Promise<StudentListResponse> {
  const url = new URL(`${API_URL}/v1/students`)
  url.searchParams.set('page', page.toString())
  url.searchParams.set('size', size.toString())

  const headers: HeadersInit = {
    'Content-Type': 'application/json',
  }

  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  }

  const response = await fetch(url.toString(), {
    headers,
    credentials: 'include',
  })
  if (!response.ok) {
    throw new Error(`Failed to fetch students: ${response.statusText}`)
  }

  return response.json()
}
