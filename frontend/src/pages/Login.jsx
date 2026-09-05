import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'

const ROLE_HOME = {
  management: '/management',
  soc_analyst: '/soc',
  security_engineer: '/engineering',
}

const DEMO_USERS = [
  { username: 'manager', label: 'Management (Alex Chen)' },
  { username: 'analyst', label: 'SOC Analyst (Priya Nair)' },
  { username: 'engineer', label: 'Security Engineer (Sam Rivera)' },
]

export default function Login() {
  const [username, setUsername] = useState('manager')
  const [password, setPassword] = useState('demo1234')
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(false)
  const { login } = useAuth()
  const navigate = useNavigate()

  async function handleSubmit(e) {
    e.preventDefault()
    setError(null)
    setLoading(true)
    try {
      const user = await login(username, password)
      navigate(ROLE_HOME[user.role] || '/')
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-950">
      <div className="w-full max-w-sm bg-slate-900 border border-slate-800 rounded-xl p-6">
        <h1 className="text-lg font-semibold mb-1">SOC Risk Platform</h1>
        <p className="text-sm text-slate-400 mb-6">Demo login — role-based dashboards</p>

        <form onSubmit={handleSubmit} className="flex flex-col gap-3">
          <div>
            <label className="text-xs text-slate-400">Demo account</label>
            <select
              className="w-full mt-1 bg-slate-800 border border-slate-700 rounded px-3 py-2 text-sm"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
            >
              {DEMO_USERS.map((u) => (
                <option key={u.username} value={u.username}>{u.label}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="text-xs text-slate-400">Password</label>
            <input
              type="password"
              className="w-full mt-1 bg-slate-800 border border-slate-700 rounded px-3 py-2 text-sm"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </div>
          {error && <div className="text-red-400 text-xs">{error}</div>}
          <button
            type="submit"
            disabled={loading}
            className="mt-2 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 rounded px-3 py-2 text-sm font-medium"
          >
            {loading ? 'Signing in…' : 'Sign in'}
          </button>
        </form>
        <p className="text-xs text-slate-500 mt-4">
          All demo accounts use password <code className="text-slate-400">demo1234</code>.
        </p>
      </div>
    </div>
  )
}
