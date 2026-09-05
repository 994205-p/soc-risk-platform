import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts'
import { api } from '../services/api'
import { KpiCard, RiskBadge, Card, LoadingState, ErrorState, StatusBadge, FreshnessBadge, ExplanationLabel } from '../components/ui'

export default function ManagementDashboard() {
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    api.managementDashboard().then(setData).catch((e) => setError(e.message))
  }, [])

  if (error) return <div className="p-6"><ErrorState message={error} /></div>
  if (!data) return <LoadingState />

  const { current_risk, kpis, control_effectiveness_summary, top_business_risks, risk_trend, experiment_summary } = data

  return (
    <div className="p-6 flex flex-col gap-6 max-w-7xl mx-auto">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-xl font-semibold text-slate-100">Executive Risk Overview</h1>
          <p className="text-sm text-slate-500">Answers: what is our business risk, and is it improving?</p>
        </div>
        <div className="flex items-center gap-3">
          <FreshnessBadge status={current_risk.data_status} />
          <RiskBadge band={current_risk.risk_band} score={current_risk.risk_score} />
        </div>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
        <KpiCard label="Current Risk" value={kpis.current_risk_score ?? 'N/A'} sub={current_risk.data_status} />
        <KpiCard label="Avg Risk Reduction" value={`${kpis.avg_risk_reduction_pct}%`} />
        <KpiCard label="Critical Vulns" value={kpis.critical_vulnerabilities} />
        <KpiCard label="Open Incidents" value={kpis.open_incidents} />
        <KpiCard label="Control Effectiveness" value={`${kpis.avg_control_effectiveness}%`} />
        <KpiCard label="Total Assets" value={kpis.total_assets} />
      </div>

      {experiment_summary && (
        <Card title="Baseline → Target → Measured Result (control-effectiveness experiment)">
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
            <div>
              <div className="text-xs text-slate-500 uppercase tracking-wide">Baseline Risk</div>
              <div className="text-xl font-semibold">{experiment_summary.baseline_risk ?? '—'}</div>
            </div>
            <div>
              <div className="text-xs text-slate-500 uppercase tracking-wide">Target Reduction</div>
              <div className="text-xl font-semibold">{experiment_summary.target_reduction_pct}%</div>
            </div>
            <div>
              <div className="text-xs text-slate-500 uppercase tracking-wide">Measured Risk</div>
              <div className="text-xl font-semibold">{experiment_summary.measured_risk ?? '—'}</div>
            </div>
            <div>
              <div className="text-xs text-slate-500 uppercase tracking-wide">Measured Reduction</div>
              <div className="text-xl font-semibold text-green-400">{experiment_summary.measured_reduction_pct}%</div>
            </div>
            <div>
              <div className="text-xs text-slate-500 uppercase tracking-wide">Target Achieved</div>
              <div className="text-xl font-semibold">
                {experiment_summary.target_achieved === null ? '—' : (
                  <StatusBadge text={experiment_summary.target_achieved ? 'YES' : 'NO'}
                                tone={experiment_summary.target_achieved ? 'good' : 'bad'} />
                )}
              </div>
            </div>
            <div>
              <div className="text-xs text-slate-500 uppercase tracking-wide">Confidence</div>
              <div className="text-xl font-semibold">{experiment_summary.confidence}%</div>
            </div>
          </div>
          <p className="text-xs text-slate-500 mt-3">
            Derived from the actual control-effectiveness measurements below — not hardcoded.
            Target reduction of {experiment_summary.target_reduction_pct}% is the organisation's documented goal
            (see docs/risk_methodology.md).
          </p>
        </Card>
      )}

      <Card title="Risk Trend (organisation-wide)">
        {risk_trend.length > 1 ? (
          <ResponsiveContainer width="100%" height={220}>
            <LineChart data={risk_trend}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
              <XAxis dataKey="snapshot_time" hide />
              <YAxis domain={[0, 100]} stroke="#64748b" fontSize={12} />
              <Tooltip contentStyle={{ background: '#0f172a', border: '1px solid #334155' }} />
              <Line type="monotone" dataKey="risk_score" stroke="#f97316" strokeWidth={2} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        ) : (
          <p className="text-sm text-slate-500">Trend will populate as more risk snapshots are recorded (refresh the risk score a few times to see a trend).</p>
        )}
      </Card>

      <Card title="Executive Explanation" right={<ExplanationLabel source={current_risk.explanation_source} label={current_risk.explanation_label} />}>
        <p className="text-sm text-slate-300 leading-relaxed">{current_risk.explanation}</p>
      </Card>

      <Card title="Control Effectiveness">
        <div className="overflow-x-auto">
          <table className="w-full text-sm min-w-[640px]">
            <thead>
              <tr className="text-left text-slate-400 border-b border-slate-800">
                <th className="py-2">Control</th>
                <th>Coverage</th>
                <th>Effectiveness</th>
                <th>Risk Reduction</th>
                <th>Attribution Confidence</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {control_effectiveness_summary.map((c) => (
                <tr key={c.control_id} className="border-b border-slate-900 hover:bg-slate-800/40">
                  <td className="py-2">
                    <Link to={`/controls/${c.control_id}`} className="hover:underline text-blue-400">
                      {c.control_name}
                    </Link>
                  </td>
                  <td>{c.coverage}%</td>
                  <td>{c.effectiveness_score}%</td>
                  <td className={c.risk_reduction_pct >= 0 ? 'text-green-400' : 'text-red-400'}>{c.risk_reduction_pct}%</td>
                  <td>{c.attribution_confidence != null ? `${c.attribution_confidence}%` : '—'}</td>
                  <td><StatusBadge text={c.status} tone={c.status === 'ACTIVE' ? 'good' : 'default'} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>

      <Card title="Top Business Risks (by business unit)">
        {top_business_risks.length === 0 ? (
          <p className="text-sm text-slate-500">No business units currently show elevated high/critical exposure.</p>
        ) : (
          <ul className="text-sm flex flex-col gap-2">
            {top_business_risks.map((r) => (
              <li key={r.business_unit} className="flex justify-between border-b border-slate-900 py-1">
                <span>{r.business_unit}</span>
                <span className="text-slate-400">{r.high_risk_asset_count} high/critical-severity exposed assets</span>
              </li>
            ))}
          </ul>
        )}
      </Card>
    </div>
  )
}
