import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider, useAuth } from './hooks/useAuth'
import NavBar from './components/NavBar'

import Login from './pages/Login'
import ManagementDashboard from './pages/ManagementDashboard'
import SocDashboard from './pages/SocDashboard'
import EngineeringDashboard from './pages/EngineeringDashboard'
import RiskDetail from './pages/RiskDetail'
import Controls from './pages/Controls'
import ControlDetail from './pages/ControlDetail'
import Assets from './pages/Assets'
import Vulnerabilities from './pages/Vulnerabilities'
import Incidents from './pages/Incidents'
import DataQuality from './pages/DataQuality'
import Legacy from './pages/Legacy'

function ProtectedRoute({ children }) {
  const { user } = useAuth()
  if (!user) return <Navigate to="/login" replace />
  return children
}

// Role-restricted route: matches the backend's role guard on the equivalent
// dashboard endpoint (see backend/app/api/dashboards.py). Frontend hiding is
// a UX convenience only -- the backend independently enforces this.
const ROLE_HOME = { management: '/management', soc_analyst: '/soc', security_engineer: '/engineering' }

function RoleRoute({ roles, children }) {
  const { user } = useAuth()
  if (!user) return <Navigate to="/login" replace />
  if (!roles.includes(user.role)) return <Navigate to={ROLE_HOME[user.role] || '/login'} replace />
  return children
}

function RoleHome() {
  const { user } = useAuth()
  if (!user) return <Navigate to="/login" replace />
  const home = { management: '/management', soc_analyst: '/soc', security_engineer: '/engineering' }
  return <Navigate to={home[user.role] || '/login'} replace />
}

function Shell({ children }) {
  return (
    <div className="flex flex-col md:flex-row min-h-screen bg-slate-950">
      <NavBar />
      <main className="flex-1 min-w-0 overflow-x-hidden">{children}</main>
    </div>
  )
}

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/" element={<RoleHome />} />

          <Route path="/management" element={<RoleRoute roles={['management']}><Shell><ManagementDashboard /></Shell></RoleRoute>} />
          <Route path="/soc" element={<RoleRoute roles={['soc_analyst', 'management']}><Shell><SocDashboard /></Shell></RoleRoute>} />
          <Route path="/engineering" element={<RoleRoute roles={['security_engineer', 'management']}><Shell><EngineeringDashboard /></Shell></RoleRoute>} />

          <Route path="/risk/:assetId" element={<ProtectedRoute><Shell><RiskDetail /></Shell></ProtectedRoute>} />
          <Route path="/controls" element={<ProtectedRoute><Shell><Controls /></Shell></ProtectedRoute>} />
          <Route path="/controls/:controlId" element={<ProtectedRoute><Shell><ControlDetail /></Shell></ProtectedRoute>} />
          <Route path="/assets" element={<ProtectedRoute><Shell><Assets /></Shell></ProtectedRoute>} />
          <Route path="/vulnerabilities" element={<ProtectedRoute><Shell><Vulnerabilities /></Shell></ProtectedRoute>} />
          <Route path="/incidents" element={<ProtectedRoute><Shell><Incidents /></Shell></ProtectedRoute>} />
          <Route path="/data-quality" element={<ProtectedRoute><Shell><DataQuality /></Shell></ProtectedRoute>} />
          <Route path="/legacy" element={<ProtectedRoute><Shell><Legacy /></Shell></ProtectedRoute>} />

          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  )
}
