const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

function getToken() {
  return localStorage.getItem('soc_token')
}

async function request(path, options = {}) {
  const token = getToken()
  const headers = { 'Content-Type': 'application/json', ...(options.headers || {}) }
  if (token) headers['Authorization'] = `Bearer ${token}`

  const res = await fetch(`${API_URL}${path}`, { ...options, headers })
  if (!res.ok) {
    let detail = res.statusText
    try {
      const body = await res.json()
      detail = body.detail || detail
    } catch (_) {}
    throw new Error(detail)
  }
  return res.json()
}

export const api = {
  login: (username, password) =>
    request('/api/auth/login', { method: 'POST', body: JSON.stringify({ username, password }) }),

  managementDashboard: () => request('/api/dashboard/management'),
  socDashboard: () => request('/api/dashboard/soc'),
  engineeringDashboard: () => request('/api/dashboard/engineering'),

  currentRisk: () => request('/api/risk/current'),
  riskTrend: (limit = 30) => request(`/api/risk/trend?limit=${limit}`),
  assetRisk: (assetId) => request(`/api/risk/assets/${assetId}`),

  controls: () => request('/api/controls'),
  controlEffectiveness: (controlId) => request(`/api/controls/${controlId}/effectiveness`),
  allControlEffectiveness: () => request('/api/controls/effectiveness'),

  vulnerabilities: (params = '') => request(`/api/vulnerabilities${params}`),
  incidents: (params = '') => request(`/api/incidents${params}`),
  remediation: (params = '') => request(`/api/remediation${params}`),

  assets: (params = '') => request(`/api/assets${params}`),
  assetEvidence: (assetId) => request(`/api/assets/${assetId}/evidence`),

  dataQuality: () => request('/api/data-quality'),

  legacyStatus: () => request('/api/legacy/status'),
  legacyMigrate: (caseIds) => request('/api/legacy/migrate', { method: 'POST', body: JSON.stringify({ case_ids: caseIds || null }) }),
  legacyVerify: (caseIds) => request('/api/legacy/verify', { method: 'POST', body: JSON.stringify({ case_ids: caseIds || null }) }),
  legacyRollback: (reason) => request('/api/legacy/rollback', { method: 'POST', body: JSON.stringify({ reason: reason || 'manual rollback' }) }),
  legacyAuditLog: () => request('/api/legacy/audit-log'),
}

export { getToken }
