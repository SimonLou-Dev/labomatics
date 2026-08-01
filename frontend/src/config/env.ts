/**
 * Environment variables configuration
 * Validated at build time and runtime
 */

export interface EnvConfig {
  baseUrl: string
  apiUrl: string
}

const getEnvVar = (key: string, fallback?: string): string => {
  const value = import.meta.env[key]
  if (!value && !fallback) {
    throw new Error(`Missing required environment variable: ${key}`)
  }
  return (value as string) || fallback || ''
}

export const env: EnvConfig = {
  baseUrl: getEnvVar('VITE_BASE_URL'),
  apiUrl: getEnvVar('VITE_API_URL'),
}

// Validate env vars exist
if (!env.baseUrl) throw new Error('VITE_BASE_URL is required')
if (!env.apiUrl) throw new Error('VITE_API_URL is required')

export default env
