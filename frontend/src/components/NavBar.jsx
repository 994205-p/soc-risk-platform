import { NavLink, useNavigate } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'

const ROLE_HOME = {
  management: '/management',
  soc_analyst: '/soc',
  security_engineer: '/engineering',
}

const ROLE_DASHBOARD_LABEL = {
  management: 'Executive Dashboard',
  soc_analyst: 'SOC Dashboard',
  security_engineer: 'Engineering Dashboard',
}

const EVIDENCE_LINKS = [
  { to: '/controls', label: 'Controls', icon: '🛡' },
  { to: '/assets', label: 'Assets', icon: '💻' },
  { to: '/vulnerabilities', label: 'Vulnerabilities', icon: '⚠' },
  { to: '/incidents', label: 'Incidents', icon: '🚨' },
  { to: '/data-quality', label: 'Data Quality', icon: '📶' },
  { to: '/legacy', label: 'Legacy & Rollback', icon: '🔁' },
]

function linkClasses(isActive) {
  return `flex items-center gap-2 px-3 py-2 rounded-lg text-sm transition-colors ${
    isActive ? 'bg-blue-950 text-blue-300 font-medium' : 'text-slate-400 hover:bg-slate-800 hover:text-slate-100'
  }`
}

// Renders ONLY the navigation chrome (desktop sidebar + mobile top bar).
// Page content is placed alongside it by the <Shell> layout in App.jsx.
export default function NavBar() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  if (!user) return null

  return (
    <>
      <aside className="md:w-56 md:min-h-screen bg-slate-900 border-b md:border-b-0 md:border-r border-slate-800 flex md:flex-col shrink-0">
        <div className="px-4 py-4 border-b border-slate-800 hidden md:block">
          <div className="font-semibold text-slate-100 text-sm">SOC Risk Platform</div>
          <div className="text-xs text-slate-500 mt-0.5">{user.displayName}</div>
          <div className="text-xs text-slate-600">{user.role.replace('_', ' ')}</div>
        </div>

        <nav className="flex md:flex-col gap-1 px-2 py-2 overflow-x-auto md:overflow-visible">
          <NavLink to={ROLE_HOME[user.role] || '/'} className={({ isActive }) => linkClasses(isActive)}>
            <span>🏠</span><span className="whitespace-nowrap">{ROLE_DASHBOARD_LABEL[user.role]}</span>
          </NavLink>
          <div className="hidden md:block text-xs text-slate-600 uppercase tracking-wide px-3 pt-3 pb-1">Evidence</div>
          {EVIDENCE_LINKS.map((l) => (
            <NavLink key={l.to} to={l.to} className={({ isActive }) => linkClasses(isActive)}>
              <span>{l.icon}</span><span className="whitespace-nowrap">{l.label}</span>
            </NavLink>
          ))}
        </nav>

        <div className="mt-auto px-3 py-3 border-t border-slate-800 hidden md:block">
          <button
            onClick={() => { logout(); navigate('/login') }}
            className="w-full px-3 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-sm"
          >
            Logout
          </button>
        </div>
      </aside>

      {/* Mobile-only top bar with logout since the sidebar becomes a horizontal strip */}
      <div className="md:hidden flex items-center justify-between px-4 py-2 bg-slate-950 border-b border-slate-800">
        <span className="text-xs text-slate-500">{user.displayName} · {user.role.replace('_', ' ')}</span>
        <button
          onClick={() => { logout(); navigate('/login') }}
          className="px-3 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs"
        >
          Logout
        </button>
      </div>
    </>
  )
}
