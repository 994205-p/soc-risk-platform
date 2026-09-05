import { useEffect, useState } from 'react'
import { api } from '../services/api'
import { Card, KpiCard, LoadingState, ErrorState, StatusBadge } from '../components/ui'

const ISSUE_TONE = { MISSING: 'bad', INVALID: 'bad', STALE: 'warn', DUPLICATE: 'warn', INCONSISTENT: 'warn' }

export default function DataQuality() {
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    api.dataQuality().then(setData).catch((e) => setError(e.message))
  }, [])

  if (error) return <div className="p-6"><ErrorState message={error} /></div>
  if (!data) return <LoadingState />

  return (
    <div className="p-6 max-w-5xl mx-auto flex flex-col gap-6">
      <h1 className="text-xl font-semibold">Data Quality & Freshness</h1>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <KpiCard label="Total DQ Events" value={data.total_events} />
        <KpiCard label="Fresh Telemetry" value={data.telemetry_freshness_breakdown.FRESH} />
        <KpiCard label="Aging Telemetry" value={data.telemetry_freshness_breakdown.AGING} />
        <KpiCard label="Stale Telemetry" value={data.telemetry_freshness_breakdown.STALE} />
      </div>

      <Card title="Issues by Type">
        <div className="flex gap-3 flex-wrap">
          {Object.entries(data.by_issue_type).map(([type, count]) => (
            <StatusBadge key={type} text={`${type}: ${count}`} tone={ISSUE_TONE[type] || 'default'} />
          ))}
        </div>
      </Card>

      <Card title="Recent Data Quality Events (evidence log)">
        <div className="overflow-x-auto"><table className="w-full text-sm">
          <thead><tr className="text-left text-slate-400 border-b border-slate-800">
            <th className="py-2">Source</th><th>Record</th><th>Issue</th><th>Detail</th><th>Severity</th>
          </tr></thead>
          <tbody>
            {data.recent_events.map((e) => (
              <tr key={e.event_id} className="border-b border-slate-900">
                <td className="py-2">{e.source_table}</td>
                <td className="text-slate-500">{e.record_id}</td>
                <td><StatusBadge text={e.issue_type} tone={ISSUE_TONE[e.issue_type] || 'default'} /></td>
                <td className="text-slate-400">{e.detail}</td>
                <td>{e.severity}</td>
              </tr>
            ))}
          </tbody>
        </table></div>
      </Card>
    </div>
  )
}
