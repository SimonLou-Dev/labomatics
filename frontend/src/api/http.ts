/**
 * HTTP client — thin axios wrapper
 * All API calls go through this client
 */
import axios from 'axios'

const http = axios.create({
  baseURL: (import.meta.env.VITE_API_URL ?? '/api') + '/v1',
  withCredentials: true,
})

let csrfToken = ''

http.interceptors.response.use((response) => {
  const token = response.headers['x-csrf-token']
  if (token) csrfToken = token
  return response
})

http.interceptors.request.use((config) => {
  // Les tokens sont dans les cookies HTTPOnly, pas de gestion manuelle
  if (csrfToken) config.headers['X-CSRF-Token'] = csrfToken

  // Set Content-Type only if not FormData
  if (!(config.data instanceof FormData)) {
    config.headers['Content-Type'] = 'application/json'
  }

  return config
})

export default http
