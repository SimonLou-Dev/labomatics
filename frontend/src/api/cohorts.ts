/**
 * Cohorts API endpoints
 */
import http from './http'
import type { CohortDTO, CohortListResponseDTO } from './types/cohorts'

export async function listCohorts(page: number, size: number): Promise<CohortListResponseDTO> {
  const res = await http.get<CohortListResponseDTO>('/cohorts', {
    params: { page, size },
  })
  return res.data
}

export async function assignClusterToCohort(cohortId: string, clusterId: string): Promise<CohortDTO> {
  const res = await http.post<CohortDTO>(`/cohorts/${cohortId}/clusters/${clusterId}`, {})
  return res.data
}

export async function removeClusterFromCohort(cohortId: string, clusterId: string): Promise<void> {
  await http.delete(`/cohorts/${cohortId}/clusters/${clusterId}`)
}

export async function setDefaultCluster(cohortId: string, clusterId: string): Promise<CohortDTO> {
  const res = await http.patch<CohortDTO>(`/cohorts/${cohortId}/clusters/${clusterId}/set-default`, {})
  return res.data
}
