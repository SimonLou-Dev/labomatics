/**
 * Clusters API endpoints
 */
import http from './http'
import type {
  ClusterDTO,
  ClusterCreateDTO,
  ClusterUpdateDTO,
  ClusterCredentialWriteDTO,
} from './types'
import type { PaginatedResponse } from './types'

export async function listClusters(
  page: number,
  perPage: number
): Promise<PaginatedResponse<ClusterDTO>> {
  const res = await http.get<PaginatedResponse<ClusterDTO>>('/clusters', {
    params: { page, size: perPage },
  })
  return res.data
}

export async function createCluster(data: ClusterCreateDTO): Promise<ClusterDTO> {
  const res = await http.post<ClusterDTO>('/clusters', data)
  return res.data
}

export async function updateCluster(
  id: string,
  data: ClusterUpdateDTO
): Promise<ClusterDTO> {
  const res = await http.patch<ClusterDTO>(`/clusters/${id}`, data)
  return res.data
}

export async function deleteCluster(id: string): Promise<void> {
  await http.delete(`/clusters/${id}`)
}

export async function setDefaultCluster(id: string): Promise<ClusterDTO> {
  const res = await http.patch<ClusterDTO>(
    `/clusters/${id}/set-default`,
    {}
  )
  return res.data
}

export async function setClusterCredential(
  id: string,
  tokenId: string,
  tokenSecret: string
): Promise<void> {
  const data: ClusterCredentialWriteDTO = {
    token_id: tokenId,
    token_secret: tokenSecret,
  }
  await http.post(`/clusters/${id}/credential`, data)
}

export async function attachIpRange(
  clusterId: string,
  ipRangeId: string
): Promise<void> {
  await http.post(`/clusters/${clusterId}/ip-ranges/${ipRangeId}`, {})
}

export async function detachIpRange(
  clusterId: string,
  ipRangeId: string
): Promise<void> {
  await http.delete(`/clusters/${clusterId}/ip-ranges/${ipRangeId}`)
}

export async function attachVxlanRange(
  clusterId: string,
  vxlanRangeId: string
): Promise<void> {
  await http.post(`/clusters/${clusterId}/vxlan-ranges/${vxlanRangeId}`, {})
}

export async function detachVxlanRange(
  clusterId: string,
  vxlanRangeId: string
): Promise<void> {
  await http.delete(`/clusters/${clusterId}/vxlan-ranges/${vxlanRangeId}`)
}

export async function applyClusterConfig(file: File): Promise<void> {
  const formData = new FormData()
  formData.append('file', file)

  await http.post('/clusters/apply-config', formData)
}

export async function testClusterConnection(id: string): Promise<{ success: boolean; message: string; nodes_count?: number; error?: string }> {
  const res = await http.post<{ success: boolean; message: string; nodes_count?: number; error?: string }>(`/clusters/${id}/test-connection`, {})
  return res.data
}
