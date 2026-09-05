import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../services/api'
import { Card, KpiCard, LoadingState, ErrorState, StatusBadge, EmptyState } from '../components/ui'

const SEV_TONE = { LOW: 'default', MEDIUM: 'warn', HIGH: 'warn', CRITICAL: 'bad' }
const SEVERITIES = ['ALL', 'CRITICAL', 'HIGH', 'MEDIUM', 'LOW']

export default function SocDashboard() {
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)
  const [incidentSeverity, setIncidentSeverity] = useState('ALL')
  const [vulnSeverity, setVulnSeverity] = useState('ALL')

  useEffect(() => {
    api.socDashboard().then(setData).catch((e) => setError(e.message))
  }, [])

  const filteredIncidents = useMemo(() => {
    if (!data) return []
    return incidentSeverity === 'ALL' ? data.active_incidents : data.active_incidents.filter((i) => i.severity === incidentSeverity)
  }, [data, incidentSeverity])

  const filteredVulns = useMemo(() => {
    if (!data) return []
    return vulnSeverity === 'ALL' ? data.open_vulnerabilities : data.open_vulnerabilities.filter((v) => v.severity === vulnSeverity)
  }, [data, vulnSeverity])

  if (error) return <div className="p-6"><ErrorState message={error} /></div>
  if (!data) return <LoadingState />

  return (
    <div className="p-6 flex flex-col gap-6 max-w-7xl mx-auto">
      <div>
        <h1 className="text-xl font-semibold text-slate-100">SOC Analyst Console</h1>
        <p className="text-sm text-slate-500">Active monitoring, investigation evidence, and remediation tracking.</p>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
        <KpiCard label="Open Incidents" value={data.counts.open_incidents} />
        <KpiCard label="Critical Incidents" value={data.counts.critical_incidents} />
        <KpiCard label="Open Vulnerabilities" value={data.counts.open_vulnerabilities} />
        <KpiCard label="Critical Assets" value={data.counts.critical_assets} />
        <KpiCard label="Remediation Backlog" value={data.counts.remediation_backlog} />
        <KpiCard label="Stale Telemetry Sources" value={data.counts.stale_telemetry_sources}
                 sub={data.counts.control_failures > 0 ? `${data.counts.control_failures} control failure(s)` : undefined} />
      </div>

      <Card
        title="Active Incidents"
        right={
          <select value={incidentSeverity} onChange={(e) => setIncidentSeverity(e.target.value)}
                  className="bg-slate-800 border border-slate-700 rounded px-2 py-1 text-xs">
            {SEVERITIES.map((s) => <option key={s} value={s}>{s === 'ALL' ? 'All severities' : s}</option>)}
          </select>
        }
      >
        {filteredIncidents.length === 0 ? <EmptyState message="No incidents match this filter." /> : (
        <div className="overflow-x-auto"><table className="w-full text-sm">
          <thead>
            <tr className="text-left text-slate-400 border-b border-slate-800">
              <th className="py-2">Incident</th><th>Asset</th><th>Asset Crit.</th><th>Type</th><th>Severity</th><th>Status</th><th>Detected</th>
            </tr>
          </thead>
          <tbody>
            {filteredIncidents.map((i) => (
              <tr key={i.incident_id} className="border-b border-slate-900 hover:bg-slate-800/40">
                <td className="py-2">{i.incident_id}</td>
                <td><Link to={`/risk/${i.asset_id}`} className="text-blue-400 hover:underline">{i.asset_id}</Link></td>
                <td>{i.asset_criticality ? <StatusBadge text={i.asset_criticality} tone={SEV_TONE[i.asset_criticality]} /> : '—'}</td>
                <td>{i.incident_type}</td>
                <td><StatusBadge text={i.severity} tone={SEV_TONE[i.severity]} /></td>
                <td>{i.status}</td>
                <td className="text-slate-500">{i.detected_at ? new Date(i.detected_at).toLocaleDateString() : '—'}</td>
              </tr>
            ))}
          </tbody>
        </table></div>
        )}
      </Card>

      <Card
        title="Open Vulnerabilities (evidence)"
        right={
          <select value={vulnSeverity} onChange={(e) => setVulnSeverity(e.target.value)}
                  className="bg-slate-800 border border-slate-700 rounded px-2 py-1 text-xs">
            {SEVERITIES.map((s) => <option key={s} value={s}>{s === 'ALL' ? 'All severities' : s}</option>)}
          </select>
        }
      >
        {filteredVulns.length === 0 ? <EmptyState message="No vulnerabilities match this filter." /> : (
        <div className="overflow-x-auto"><table className="w-full text-sm">
          <thead>
            <tr className="text-left text-slate-400 border-b border-slate-800">
              <th className="py-2">Vulnerability</th><th>Asset</th><th>Severity</th><th>CVSS</th><th>Exploit?</th><th>Internet-exposed?</th>
            </tr>
          </thead>
          <tbody>
            {filteredVulns.map((v) => (
              <tr key={v.vulnerability_id} className="border-b border-slate-900 hover:bg-slate-800/40">
                <td className="py-2">{v.vulnerability_id}</td>
                <td><Link to={`/risk/${v.asset_id}`} className="text-blue-400 hover:underline">{v.asset_id}</Link></td>
                <td><StatusBadge text={v.severity} tone={SEV_TONE[v.severity]} /></td>
                <td>{v.cvss_score}</td>
                <td>{v.exploit_available ? 'Yes' : 'No'}</td>
                <td>{v.internet_exposed ? 'Yes' : 'No'}</td>
              </tr>
            ))}
          </tbody>
        </table></div>
        )}
      </Card>

      <Card title="Critical Assets">
        {data.critical_assets.length === 0 ? <EmptyState message="No CRITICAL-criticality assets on record." /> : (
          <ul className="text-sm flex flex-col gap-1">
            {data.critical_assets.map((a) => (
              <li key={a.asset_id} className="flex justify-between border-b border-slate-900 py-1.5">
                <Link to={`/risk/${a.asset_id}`} className="text-blue-400 hover:underline">{a.asset_name}</Link>
                <span className="text-slate-500">{a.business_unit} {a.internet_exposed && '· internet-exposed'}</span>
              </li>
            ))}
          </ul>
        )}
      </Card>
    </div>
  )
}
