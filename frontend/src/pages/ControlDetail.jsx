import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { api } from '../services/api'
import { Card, LoadingState, ErrorState, StatusBadge, FreshnessBadge } from '../components/ui'

export default function ControlDetail() {
  const { controlId } = useParams()
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    setData(null)
    api.controlEffectiveness(controlId).then(setData).catch((e) => setError(e.message))
  }, [controlId])

  if (error) return <div className="p-6"><ErrorState message={error} /></div>
  if (!data) return <LoadingState />

  return (
    <div className="p-6 max-w-4xl mx-auto flex flex-col gap-6">
      <div>
        <h1 className="text-xl font-semibold">{data.control_name}</h1>
        <p className="text-sm text-slate-500">{data.control_id} · {data.status}</p>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card title="Risk Before"><div className="text-2xl">{data.risk_before}</div></Card>
        <Card title="Risk After"><div className="text-2xl">{data.risk_after}</div></Card>
        <Card title="Risk Reduction"><div className={`text-2xl ${data.risk_reduction_pct >= 0 ? 'text-green-400' : 'text-red-400'}`}>{data.risk_reduction_pct}%</div></Card>
        <Card title="Target Achieved">
          <div className="text-2xl">
            <StatusBadge text={data.target_achieved ? 'YES' : 'NO'} tone={data.target_achieved ? 'good' : 'bad'} />
            <span className="text-xs text-slate-500 block mt-1">Target: {data.target_reduction_pct}%</span>
          </div>
        </Card>
      </div>

      <Card title="Attribution & Confidence" right={<FreshnessBadge status={data.telemetry_freshness} />}>
        <div className="grid grid-cols-2 gap-4 text-sm mb-3">
          <div>
            <div className="text-slate-500 text-xs">Attribution Confidence</div>
            <div className="text-xl">{data.attribution_confidence}%</div>
          </div>
          <div>
            <div className="text-slate-500 text-xs">Measurement Confidence</div>
            <div className="text-xl">{data.confidence}%</div>
          </div>
        </div>

        {data.attribution_evidence?.length > 0 && (
          <div className="mb-3">
            <div className="text-xs text-slate-400 font-medium mb-1">Supporting evidence</div>
            <ul className="text-sm text-slate-300 list-disc list-inside space-y-0.5">
              {data.attribution_evidence.map((e, i) => <li key={i}>{e}</li>)}
            </ul>
          </div>
        )}

        {data.confounding_factors?.length > 0 && (
          <div className="mb-3">
            <div className="text-xs text-yellow-400 font-medium mb-1">Confounding factors (reduce confidence)</div>
            <ul className="text-sm text-yellow-300/90 list-disc list-inside space-y-0.5">
              {data.confounding_factors.map((c, i) => <li key={i}>{c}</li>)}
            </ul>
          </div>
        )}

        <p className="text-xs text-slate-500 border-t border-slate-800 pt-3 mt-3">{data.causation_disclaimer}</p>
      </Card>

      <Card title="Coverage / Compliance (before → after)">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
          <div><div className="text-slate-500 text-xs">Baseline Coverage</div>{data.baseline_coverage ?? '—'}%</div>
          <div><div className="text-slate-500 text-xs">Current Coverage</div>{data.actual_coverage}%</div>
          <div><div className="text-slate-500 text-xs">Baseline Compliance</div>{data.baseline_compliance ?? '—'}%</div>
          <div><div className="text-slate-500 text-xs">Current Compliance</div>{data.compliance}%</div>
        </div>
      </Card>

      <Card title="Before vs After">
        <div className="grid grid-cols-2 gap-4 text-sm">
          <div>
            <div className="text-slate-400 font-medium mb-1">Baseline</div>
            <div>Vulnerabilities: {data.vulnerabilities_before}</div>
            <div>Incidents: {data.incidents_before}</div>
          </div>
          <div>
            <div className="text-slate-400 font-medium mb-1">Current</div>
            <div>Vulnerabilities: {data.vulnerabilities_after}</div>
            <div>Incidents: {data.incidents_after}</div>
          </div>
        </div>
      </Card>

      <Card title="Risk Component Breakdown">
        <div className="overflow-x-auto">
          <table className="w-full text-sm min-w-[400px]">
            <thead><tr className="text-left text-slate-400 border-b border-slate-800">
              <th className="py-2">Component</th><th>Before</th><th>After</th>
            </tr></thead>
            <tbody>
              {Object.keys(data.risk_before_components).map((k) => (
                <tr key={k} className="border-b border-slate-900">
                  <td className="py-2">{k.replace(/_/g, ' ')}</td>
                  <td>{data.risk_before_components[k]}</td>
                  <td>{data.risk_after_components[k]}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  )
}
