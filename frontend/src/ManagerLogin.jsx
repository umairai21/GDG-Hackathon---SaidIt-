import { useState } from 'react'
import { api } from './api.js'
import { Button, Icon } from './ui.jsx'

// Shown on /store until the manager signs in. The server enforces this too:
// every /store API call is refused without the session cookie.
export default function ManagerLogin({ onSignedIn }) {
  const [password, setPassword] = useState('')
  const [error, setError] = useState(null)
  const [busy, setBusy] = useState(false)

  async function submit(e) {
    e.preventDefault()
    setBusy(true)
    setError(null)
    try {
      await api.login(password)
      onSignedIn()
    } catch (err) {
      setError(err.status === 401 ? 'That password is not right.' : `Couldn't reach the server (${err.message})`)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="mx-auto flex min-h-[60vh] max-w-sm flex-col justify-center">
      <div className="rounded-3xl border border-slate-200 bg-white p-8 shadow-sm">
        <div className="grid h-12 w-12 place-items-center rounded-2xl bg-sky-100 text-2xl">🏪</div>
        <h1 className="mt-4 text-xl font-semibold tracking-tight">Store manager sign-in</h1>
        <p className="mt-1 text-sm text-slate-500">The store dashboard is for store staff only.</p>

        <form onSubmit={submit} className="mt-6 space-y-3">
          <label className="block">
            <span className="text-sm font-medium text-slate-700">Password</span>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoFocus
              autoComplete="current-password"
              className="mt-1 w-full rounded-xl border border-slate-300 px-3.5 py-2.5 outline-none transition focus:border-emerald-600 focus:ring-4 focus:ring-emerald-100"
            />
          </label>
          {error && (
            <div className="flex items-center gap-2 text-sm text-rose-700">
              <Icon name="alert" className="h-4 w-4" /> {error}
            </div>
          )}
          <Button variant="primary" size="md" className="w-full" disabled={busy || !password}>
            {busy ? 'Signing in…' : 'Sign in'}
          </Button>
        </form>
      </div>
      {/* Only points toward the public customer side; nothing on the customer side points back here. */}
      <a href="/shop" className="mt-4 inline-flex items-center justify-center gap-1.5 text-sm text-slate-500 hover:text-slate-900">
        Not the store manager? Continue as a customer <Icon name="arrow" className="h-4 w-4" />
      </a>
    </div>
  )
}
