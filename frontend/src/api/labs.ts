/**
 * Labs API endpoints
 */
import http from './http'
import type { JobDTO } from './types'

export async function createLab(clusterId?: string): Promise<JobDTO> {
  const params = clusterId ? { cluster_id: clusterId } : {}
  const res = await http.post<JobDTO>('/labs', {}, { params })
  return res.data
}
