import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../services/api'
import { Card, KpiCard, LoadingState, ErrorState, StatusBadge, FreshnessBadge, EmptyState } from '../components/ui'

export default function EngineeringDashboard() {
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    api.engineeringDashboard().then(setData).catch((e) => setError(e.message))
  }, [])

  if (error) return <div className="p-6"><ErrorState message={error} /></div>
  if (!data) return <LoadingState />

  const tf = data.telemetry_freshness || {}

  return (
    <div className="p-6 flex flex-col gap-6 max-w-7xl mx-auto">
      <div>
        <h1 className="text-xl font-semibold text-slate-100">Security Engineering Console</h1>
        <p className="text-sm text-slate-500">Control health, telemetry freshness, and patch compliance.</p>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4">
        <KpiCard label="Patch Compliance" value={data.patch_compliance_pct != null ? `${data.patch_compliance_pct}%` : 'N/A'} />
        <KpiCard label="Remediation Pending" value={data.remediation_pending} />
        <KpiCard label="Underperforming Controls" value={data.failed_controls.length} />
        <KpiCard label="Fresh Telemetry Sources" value={tf.FRESH ?? 0} />
        <KpiCard label="Stale/Missing/Invalid" value={(tf.STALE ?? 0) + (tf.MISSING ?? 0) + (tf.INVALID ?? 0)} />
      </div>

      <Card title="Telemetry Freshness Breakdown">
        <div className="flex gap-4 flex-wrap text-sm">
          {['FRESH', 'AGING', 'STALE', 'MISSING', 'INVALID'].map((k) => (
            <div key={k} className="flex items-center gap-2">
              <FreshnessBadge status={k} />
              <span className="text-slate-400">{tf[k] ?? 0}</span>
            </div>
          ))}
        </div>
      </Card>

      <Card title="Control Coverage & Compliance">
        <div className="overflow-x-auto"><table className="w-full text-sm">
          <thead>
            <tr className="text-left text-slate-400 border-b border-slate-800">
              <th className="py-2">Control</th><th>Target</th><th>Actual</th><th>Status</th>
            </tr>
          </thead>
          <tbody>
            {data.controls.map((c) => {
              const gap = (c.target_coverage || 0) - (c.actual_coverage || 0)
              return (
                <tr key={c.control_id} className="border-b border-slate-900 hover:bg-slate-800/40">
                  <td className="py-2">
                    <Link to={`/controls/${c.control_id}`} className="text-blue-400 hover:underline">{c.control_name}</Link>
                  </td>
                  <td>{c.target_coverage}%</td>
                  <td>{c.actual_coverage}%</td>
                  <td>
                    <StatusBadge text={gap > 10 ? 'GAP' : 'ON TARGET'} tone={gap > 10 ? 'bad' : 'good'} />
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table></div>
      </Card>

      <Card title="Failed / Underperforming Controls">
        {data.failed_controls.length === 0 ? (
          <EmptyState message="No controls currently missing target coverage by more than 15 points." />
        ) : (
          <div className="overflow-x-auto"><table className="w-full text-sm">
            <thead>
              <tr className="text-left text-slate-400 border-b border-slate-800">
                <th className="py-2">Control</th><th>Coverage</th><th>Effectiveness</th><th>Confidence</th>
              </tr>
            </thead>
            <tbody>
              {data.failed_controls.map((c) => (
                <tr key={c.control_id} className="border-b border-slate-900 hover:bg-slate-800/40">
                  <td className="py-2">
                    <Link to={`/controls/${c.control_id}`} className="text-blue-400 hover:underline">{c.control_name}</Link>
                  </td>
                  <td>{c.actual_coverage}%</td>
                  <td>{c.effectiveness_score}%</td>
                  <td>{c.confidence}%</td>
                </tr>
              ))}
            </tbody>
          </table></div>
        )}
      </Card>

      <Card title="Full Control Effectiveness Detail">
        <div className="overflow-x-auto"><table className="w-full text-sm">
          <thead>
            <tr className="text-left text-slate-400 border-b border-slate-800">
              <th className="py-2">Control</th><th>Risk Before</th><th>Risk After</th><th>Reduction</th><th>Attribution</th><th>Confidence</th>
            </tr>
          </thead>
          <tbody>
            {data.effectiveness.map((e) => (
              <tr key={e.control_id} className="border-b border-slate-900 hover:bg-slate-800/40">
                <td className="py-2">
                  <Link to={`/controls/${e.control_id}`} className="text-blue-400 hover:underline">{e.control_name}</Link>
                </td>
                <td>{e.risk_before}</td>
                <td>{e.risk_after}</td>
                <td className={e.risk_reduction_pct >= 0 ? 'text-green-400' : 'text-red-400'}>{e.risk_reduction_pct}%</td>
                <td>{e.attribution_confidence}%</td>
                <td>{e.confidence}%</td>
              </tr>
            ))}
          </tbody>
        </table></div>
      </Card>
    </div>
  )
}
