import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react'
import { apiClient } from './apiClient'

// The signed-in seat.
//
// One account per seat — the four CPSE stewards and the national approver — so signing in is
// choosing who you are, and the server takes the role from the token it signed rather than
// from anything the browser says. Every request carries the token; a 401 from anywhere means
// the session is over and the door is shown again.

export interface Session {
  token: string
  username: string
  role: 'steward' | 'national_approver'
  org: string | null
  label: string
  actor_name: string
}

const STORAGE_KEY = 'meridian:session'

function stored(): Session | null {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    return raw ? (JSON.parse(raw) as Session) : null
  } catch {
    return null
  }
}

interface AuthContextValue {
  session: Session | null
  /** Resolves on success; throws with the server's message otherwise. */
  login: (username: string, password: string) => Promise<void>
  logout: () => void
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<Session | null>(stored)

  // The token travels on every request; the interceptor reads whatever session is current.
  useEffect(() => {
    const req = apiClient.interceptors.request.use((config) => {
      if (session?.token) config.headers.Authorization = `Bearer ${session.token}`
      return config
    })
    const res = apiClient.interceptors.response.use(
      (r) => r,
      (error) => {
        const status = (error as { response?: { status?: number } })?.response?.status
        const url = (error as { config?: { url?: string } })?.config?.url ?? ''
        if (status === 401 && !url.includes('/auth/login')) {
          setSession(null)
          try { localStorage.removeItem(STORAGE_KEY) } catch { /* nothing to clear */ }
        }
        return Promise.reject(error)
      },
    )
    return () => {
      apiClient.interceptors.request.eject(req)
      apiClient.interceptors.response.eject(res)
    }
  }, [session])

  const login = useCallback(async (username: string, password: string) => {
    try {
      const { data } = await apiClient.post<Session>('/auth/login', { username, password })
      setSession(data)
      try { localStorage.setItem(STORAGE_KEY, JSON.stringify(data)) } catch { /* per-viewer */ }
    } catch (error) {
      const detail = (error as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      throw new Error(detail ?? 'Could not reach the server.')
    }
  }, [])

  const logout = useCallback(() => {
    setSession(null)
    try { localStorage.removeItem(STORAGE_KEY) } catch { /* nothing to clear */ }
  }, [])

  const value = useMemo(() => ({ session, login, logout }), [session, login, logout])
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used inside AuthProvider')
  return ctx
}
