/**
 * VXLAN Ranges API endpoints
 */
import http from './http'
import type { VxlanRangeDTO, VxlanRangeCreateDTO, VxlanRangeUpdateDTO, VxlanAllocationDTO } from './types'
import type { PaginatedResponse } from './types'

export async function listVxlanRanges(
  page: number,
  perPage: number
): Promise<PaginatedResponse<VxlanRangeDTO>> {
  const res = await http.get<PaginatedResponse<VxlanRangeDTO>>('/vxlan-ranges', {
    params: { page, size: perPage },
  })
  return res.data
}

export async function createVxlanRange(data: VxlanRangeCreateDTO): Promise<VxlanRangeDTO> {
  const res = await http.post<VxlanRangeDTO>('/vxlan-ranges', data)
  return res.data
}

export async function updateVxlanRange(
  id: string,
  data: VxlanRangeUpdateDTO
): Promise<VxlanRangeDTO> {
  const res = await http.patch<VxlanRangeDTO>(`/vxlan-ranges/${id}`, data)
  return res.data
}

export async function deleteVxlanRange(id: string): Promise<void> {
  await http.delete(`/vxlan-ranges/${id}`)
}

export async function getVxlanRange(rangeId: string): Promise<VxlanRangeDTO> {
  const res = await http.get<VxlanRangeDTO>(`/vxlan-ranges/${rangeId}`)
  return res.data
}

export async function getVxlanRangeAllocations(rangeId: string): Promise<VxlanAllocationDTO[]> {
  const res = await http.get<VxlanAllocationDTO[]>(`/vxlan-ranges/${rangeId}/allocations`)
  return res.data
}
