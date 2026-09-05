import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { api } from '../services/api'
import { Card, RiskBadge, FreshnessBadge, LoadingState, ErrorState, StatusBadge, ExplanationLabel } from '../components/ui'

export default function RiskDetail() {
  const { assetId } = useParams()
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    setData(null)
    api.assetEvidence(assetId).then(setData).catch((e) => setError(e.message))
  }, [assetId])

  if (error) return <div className="p-6"><ErrorState message={error} /></div>
  if (!data) return <LoadingState />

  const { asset, risk, vulnerabilities, incidents, controls, remediation_history } = data

  return (
    <div className="p-6 flex flex-col gap-6 max-w-5xl mx-auto">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold">{asset.asset_name}</h1>
          <p className="text-sm text-slate-500">{asset.asset_id} · {asset.asset_type} · {asset.business_unit} · {asset.criticality} criticality</p>
        </div>
        <RiskBadge band={risk.risk_band} score={risk.risk_score} />
      </div>

      <Card title="Why this score" right={<ExplanationLabel source={risk.explanation_source} label={risk.explanation_label} />}>
        <p className="text-sm text-slate-300 leading-relaxed">{risk.explanation}</p>
        <div className="mt-3 flex gap-4 text-xs text-slate-400">
          <span>Confidence: {risk.confidence}%</span>
          <FreshnessBadge status={risk.data_status} />
          {risk.fallback && <span className="text-red-400">FALLBACK snapshot in use</span>}
        </div>
      </Card>

      {risk.components && (
        <Card title="Risk Score Components">
          <div className="grid grid-cols-4 gap-3 text-sm">
            <div><div className="text-slate-500 text-xs">Vulnerability</div><div>{risk.components.vulnerability_component} / 35</div></div>
            <div><div className="text-slate-500 text-xs">Incident</div><div>{risk.components.incident_component} / 25</div></div>
            <div><div className="text-slate-500 text-xs">Control Gap</div><div>{risk.components.control_gap_component} / 25</div></div>
            <div><div className="text-slate-500 text-xs">Asset Criticality</div><div>{risk.components.asset_criticality_component} / 15</div></div>
          </div>
        </Card>
      )}

      <Card title={`Vulnerabilities (${vulnerabilities.length})`}>
        {vulnerabilities.length === 0 ? <p className="text-sm text-slate-500">None on record for this asset.</p> : (
          <div className="overflow-x-auto"><table className="w-full text-sm">
            <thead><tr className="text-left text-slate-400 border-b border-slate-800">
              <th className="py-2">CVE</th><th>Severity</th><th>CVSS</th><th>Status</th><th>Exploit?</th>
            </tr></thead>
            <tbody>
              {vulnerabilities.map((v) => (
                <tr key={v.vulnerability_id} className="border-b border-slate-900">
                  <td className="py-2">{v.cve_id}</td>
                  <td>{v.severity}</td>
                  <td>{v.cvss_score}</td>
                  <td>{v.remediation_status}</td>
                  <td>{v.exploit_available ? 'Yes' : 'No'}</td>
                </tr>
              ))}
            </tbody>
          </table></div>
        )}
      </Card>

      <Card title={`Incidents (${incidents.length})`}>
        {incidents.length === 0 ? <p className="text-sm text-slate-500">None on record for this asset.</p> : (
          <div className="overflow-x-auto"><table className="w-full text-sm">
            <thead><tr className="text-left text-slate-400 border-b border-slate-800">
              <th className="py-2">Type</th><th>Severity</th><th>Status</th><th>Related control</th><th>Root cause</th>
            </tr></thead>
            <tbody>
              {incidents.map((i) => (
                <tr key={i.incident_id} className="border-b border-slate-900">
                  <td className="py-2">{i.incident_type}</td>
                  <td>{i.severity}</td>
                  <td>{i.status}</td>
                  <td>{i.control_related || '—'}</td>
                  <td className="text-slate-400">{i.root_cause}</td>
                </tr>
              ))}
            </tbody>
          </table></div>
        )}
      </Card>

      <Card title="Control Telemetry">
        {controls.length === 0 ? <p className="text-sm text-slate-500">No current telemetry for this asset.</p> : (
          <div className="overflow-x-auto"><table className="w-full text-sm">
            <thead><tr className="text-left text-slate-400 border-b border-slate-800">
              <th className="py-2">Control</th><th>Coverage</th><th>Compliance</th><th>Health</th><th>Freshness</th>
            </tr></thead>
            <tbody>
              {controls.map((c, idx) => (
                <tr key={idx} className="border-b border-slate-900">
                  <td className="py-2">{c.control_name}</td>
                  <td>{c.coverage_percentage}%</td>
                  <td>{c.compliance_percentage}%</td>
                  <td><StatusBadge text={c.health_status} tone={c.health_status === 'HEALTHY' ? 'good' : c.health_status === 'DEGRADED' ? 'warn' : 'bad'} /></td>
                  <td><FreshnessBadge status={c.freshness_status} /></td>
                </tr>
              ))}
            </tbody>
          </table></div>
        )}
      </Card>

      <Card title="Remediation History">
        {remediation_history.length === 0 ? <p className="text-sm text-slate-500">No remediation records for this asset.</p> : (
          <div className="overflow-x-auto"><table className="w-full text-sm">
            <thead><tr className="text-left text-slate-400 border-b border-slate-800">
              <th className="py-2">Vulnerability</th><th>Status</th><th>Verification</th><th>Completed</th>
            </tr></thead>
            <tbody>
              {remediation_history.map((r) => (
                <tr key={r.remediation_id} className="border-b border-slate-900">
                  <td className="py-2">{r.vulnerability_id}</td>
                  <td>{r.status}</td>
                  <td>{r.verification_status}</td>
                  <td className="text-slate-500">{r.completed_date || '—'}</td>
                </tr>
              ))}
            </tbody>
          </table></div>
        )}
      </Card>
    </div>
  )
}
