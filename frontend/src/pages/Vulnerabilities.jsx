import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../services/api'
import { Card, LoadingState, ErrorState, StatusBadge, EmptyState } from '../components/ui'

const SEV_TONE = { LOW: 'default', MEDIUM: 'warn', HIGH: 'warn', CRITICAL: 'bad' }

export default function Vulnerabilities() {
  const [vulns, setVulns] = useState(null)
  const [error, setError] = useState(null)
  const [severity, setSeverity] = useState('')

  useEffect(() => {
    const q = severity ? `?severity=${severity}` : ''
    setVulns(null)
    api.vulnerabilities(q).then(setVulns).catch((e) => setError(e.message))
  }, [severity])

  return (
    <div className="p-6 max-w-6xl mx-auto">
      <div className="flex items-center justify-between mb-4">
        <h1 className="text-xl font-semibold">Vulnerability Management</h1>
        <select
          className="bg-slate-800 border border-slate-700 rounded px-3 py-1.5 text-sm"
          value={severity}
          onChange={(e) => setSeverity(e.target.value)}
        >
          <option value="">All severities</option>
          <option value="CRITICAL">Critical</option>
          <option value="HIGH">High</option>
          <option value="MEDIUM">Medium</option>
          <option value="LOW">Low</option>
        </select>
      </div>
      {error && <ErrorState message={error} />}
      {!vulns ? <LoadingState /> : vulns.length === 0 ? <EmptyState message="No vulnerabilities match this filter." /> : (
        <Card>
          <div className="overflow-x-auto"><table className="w-full text-sm">
            <thead><tr className="text-left text-slate-400 border-b border-slate-800">
              <th className="py-2">CVE</th><th>Asset</th><th>Severity</th><th>CVSS</th><th>Status</th><th>Exploit?</th>
            </tr></thead>
            <tbody>
              {vulns.map((v) => (
                <tr key={v.vulnerability_id} className="border-b border-slate-900">
                  <td className="py-2">{v.cve_id}</td>
                  <td><Link to={`/risk/${v.asset_id}`} className="text-blue-400 hover:underline">{v.asset_id}</Link></td>
                  <td><StatusBadge text={v.severity} tone={SEV_TONE[v.severity]} /></td>
                  <td>{v.cvss_score}</td>
                  <td>{v.remediation_status}</td>
                  <td>{v.exploit_available ? 'Yes' : 'No'}</td>
                </tr>
              ))}
            </tbody>
          </table></div>
        </Card>
      )}
    </div>
  )
}
