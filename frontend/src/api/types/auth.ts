/**
 * Auth types
 */

export interface AuthUser {
  subject: string
  username: string
  email?: string
  roles: string[]
}

export interface MeDTO {
  subject: string
  username: string
  roles: string[]
}

export interface AuthResponse {
  logout_url?: string
  message?: string
}
