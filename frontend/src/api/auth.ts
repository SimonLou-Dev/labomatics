/**
 * Auth API endpoints
 */
import http from './http'
import type { MeDTO } from './types'

export async function getMe(): Promise<MeDTO> {
  const res = await http.get<MeDTO>('/auth/me')
  return res.data
}
