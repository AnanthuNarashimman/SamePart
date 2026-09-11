import { useState, type FormEvent } from 'react'
import { useAuth } from '../lib/auth'

// The door. One field pair, one sentence about what a seat is, no marketing. The usernames are
// listed because they are seats, not secrets; the passwords are not.
export function Login() {
  const { login } = useAuth()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  const submit = async (e: FormEvent) => {
    e.preventDefault()
    setBusy(true)
    setError(null)
    try {
      await login(username.trim(), password)
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="flex h-screen w-screen items-center justify-center app-canvas p-6">
      <form
        onSubmit={submit}
        className="w-full max-w-sm rounded-2xl border border-stone-100 bg-white p-7 shadow-sm"
      >
        <div className="mb-6 flex items-center gap-3">
          <img src="/logo.png" alt="" className="h-12 w-12 object-contain" />
          <div>
            <p className="text-base font-semibold tracking-wide text-stone-900">Meridian</p>
            <p className="text-xs text-stone-400">Sign in to your seat</p>
          </div>
        </div>

        <label className="mb-1.5 block text-xs font-medium text-stone-500" htmlFor="username">
          Username
        </label>
        <input
          id="username"
          autoComplete="username"
          autoFocus
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          className="mb-4 w-full rounded-lg border border-stone-200 bg-white px-3 py-2 text-sm text-stone-800 focus:border-primary-300 focus:outline-none"
        />

        <label className="mb-1.5 block text-xs font-medium text-stone-500" htmlFor="password">
          Password
        </label>
        <input
          id="password"
          type="password"
          autoComplete="current-password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          className="mb-5 w-full rounded-lg border border-stone-200 bg-white px-3 py-2 text-sm text-stone-800 focus:border-primary-300 focus:outline-none"
        />

        {error && (
          <p role="alert" className="mb-4 rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-xs text-rose-700">
            {error}
          </p>
        )}

        <button
          type="submit"
          disabled={busy || !username || !password}
          className="w-full rounded-lg bg-primary-500 py-2.5 text-sm font-medium text-white hover:bg-primary-600 disabled:cursor-not-allowed disabled:opacity-60"
        >
          {busy ? 'Signing in…' : 'Sign in'}
        </button>

        <p className="mt-5 border-t border-stone-100 pt-4 text-[11px] leading-relaxed text-stone-400">
          A seat is an organisation and a role. Stewards sign in as{' '}
          <span className="font-mono text-stone-500">bpcl</span>,{' '}
          <span className="font-mono text-stone-500">cpcl</span>,{' '}
          <span className="font-mono text-stone-500">iocl</span> or{' '}
          <span className="font-mono text-stone-500">ntpc</span> and decide within their own
          CPSE. <span className="font-mono text-stone-500">national</span> confirms identity
          across CPSEs and mints national codes.
        </p>
      </form>
    </div>
  )
}
