/**
 * IP Ranges API endpoints
 */
import http from './http'
import type {
  IpRangeDTO,
  IpRangeCreateDTO,
  IpRangeUpdateDTO,
  IpAllocationPaginatedDTO,
} from './types'
import type { PaginatedResponse } from './types'

export async function listIpRanges(
  page: number,
  perPage: number
): Promise<PaginatedResponse<IpRangeDTO>> {
  const res = await http.get<PaginatedResponse<IpRangeDTO>>('/ip-ranges', {
    params: { page, size: perPage },
  })
  return res.data
}

export async function createIpRange(data: IpRangeCreateDTO): Promise<IpRangeDTO> {
  const res = await http.post<IpRangeDTO>('/ip-ranges', data)
  return res.data
}

export async function updateIpRange(
  id: string,
  data: IpRangeUpdateDTO
): Promise<IpRangeDTO> {
  const res = await http.patch<IpRangeDTO>(`/ip-ranges/${id}`, data)
  return res.data
}

export async function deleteIpRange(id: string): Promise<void> {
  await http.delete(`/ip-ranges/${id}`)
}

export async function getIpRange(rangeId: string): Promise<IpRangeDTO> {
  const res = await http.get<IpRangeDTO>(`/ip-ranges/${rangeId}`)
  return res.data
}

export async function getIpRangeAllocations(
  rangeId: string,
  page: number = 1,
  size: number = 20,
  search?: string
): Promise<IpAllocationPaginatedDTO> {
  const res = await http.get<IpAllocationPaginatedDTO>(`/ip-ranges/${rangeId}/allocations`, {
    params: {
      page,
      size,
      ...(search && { search }),
    },
  })
  return res.data
}
