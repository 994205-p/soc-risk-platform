import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../services/api'
import { Card, LoadingState, ErrorState, StatusBadge, EmptyState } from '../components/ui'

const CRIT_TONE = { LOW: 'default', MEDIUM: 'warn', HIGH: 'warn', CRITICAL: 'bad' }

export default function Assets() {
  const [assets, setAssets] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    api.assets('?limit=100').then(setAssets).catch((e) => setError(e.message))
  }, [])

  if (error) return <div className="p-6"><ErrorState message={error} /></div>
  if (!assets) return <LoadingState />

  return (
    <div className="p-6 max-w-6xl mx-auto">
      <h1 className="text-xl font-semibold mb-4">Asset Inventory</h1>
      <p className="text-sm text-slate-500 mb-4">Showing first 100 assets. Click any asset to see its risk drill-down.</p>
      <Card>
        {assets.length === 0 ? <EmptyState message="No assets found." /> : (
        <div className="overflow-x-auto"><table className="w-full text-sm">
          <thead><tr className="text-left text-slate-400 border-b border-slate-800">
            <th className="py-2">Asset</th><th>Type</th><th>Business Unit</th><th>Criticality</th><th>Internet-exposed?</th>
          </tr></thead>
          <tbody>
            {assets.map((a) => (
              <tr key={a.asset_id} className="border-b border-slate-900">
                <td className="py-2">
                  <Link to={`/risk/${a.asset_id}`} className="text-blue-400 hover:underline">{a.asset_name}</Link>
                </td>
                <td>{a.asset_type}</td>
                <td>{a.business_unit}</td>
                <td><StatusBadge text={a.criticality} tone={CRIT_TONE[a.criticality]} /></td>
                <td>{a.internet_exposed ? 'Yes' : 'No'}</td>
              </tr>
            ))}
          </tbody>
        </table></div>
        )}
      </Card>
    </div>
  )
}
