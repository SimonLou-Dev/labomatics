/**
 * Auth API endpoints
 */
import http from './http'
import type { MeDTO, AuthResponse } from './types'

export async function getMe(): Promise<MeDTO> {
  const res = await http.get<MeDTO>('/auth/me')
  return res.data
}

export async function logout(): Promise<AuthResponse> {
  const res = await http.get<AuthResponse>('/auth/logout')
  return res.data
}
