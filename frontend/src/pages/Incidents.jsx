import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../services/api'
import { Card, LoadingState, ErrorState, StatusBadge, EmptyState } from '../components/ui'

const SEV_TONE = { LOW: 'default', MEDIUM: 'warn', HIGH: 'warn', CRITICAL: 'bad' }

export default function Incidents() {
  const [incidents, setIncidents] = useState(null)
  const [error, setError] = useState(null)
  const [status, setStatus] = useState('')

  useEffect(() => {
    const q = status ? `?status=${status}` : ''
    setIncidents(null)
    api.incidents(q).then(setIncidents).catch((e) => setError(e.message))
  }, [status])

  return (
    <div className="p-6 max-w-6xl mx-auto">
      <div className="flex items-center justify-between mb-4">
        <h1 className="text-xl font-semibold">Incident Management</h1>
        <select
          className="bg-slate-800 border border-slate-700 rounded px-3 py-1.5 text-sm"
          value={status}
          onChange={(e) => setStatus(e.target.value)}
        >
          <option value="">All statuses</option>
          <option value="OPEN">Open</option>
          <option value="RESOLVED">Resolved</option>
        </select>
      </div>
      {error && <ErrorState message={error} />}
      {!incidents ? <LoadingState /> : incidents.length === 0 ? <EmptyState message="No incidents match this filter." /> : (
        <Card>
          <div className="overflow-x-auto"><table className="w-full text-sm">
            <thead><tr className="text-left text-slate-400 border-b border-slate-800">
              <th className="py-2">Incident</th><th>Asset</th><th>Type</th><th>Severity</th><th>Status</th><th>Financial Impact (est.)</th>
            </tr></thead>
            <tbody>
              {incidents.map((i) => (
                <tr key={i.incident_id} className="border-b border-slate-900">
                  <td className="py-2">{i.incident_id}</td>
                  <td><Link to={`/risk/${i.asset_id}`} className="text-blue-400 hover:underline">{i.asset_id}</Link></td>
                  <td>{i.incident_type}</td>
                  <td><StatusBadge text={i.severity} tone={SEV_TONE[i.severity]} /></td>
                  <td>{i.status}</td>
                  <td>${i.financial_impact_estimate?.toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table></div>
        </Card>
      )}
    </div>
  )
}
