import axios from 'axios'

// The API lives under /api on whichever host serves it. Locally the dev server proxies that
// path; on Vercel the host comes from VITE_API_BASE_URL. The value is normalised so that
// "https://host", "https://host/" and "https://host/api" all mean the same thing — the first
// deploy set the bare host and every request 404ed at /auth/login.
function baseUrl(): string {
  const raw = (import.meta.env.VITE_API_BASE_URL as string | undefined)?.trim()
  if (!raw) return '/api'
  const trimmed = raw.replace(/\/+$/, '')
  return trimmed.endsWith('/api') ? trimmed : `${trimmed}/api`
}

export const apiClient = axios.create({ baseURL: baseUrl() })
