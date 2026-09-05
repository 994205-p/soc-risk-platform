import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../services/api'
import { Card, LoadingState, ErrorState, StatusBadge } from '../components/ui'

export default function Controls() {
  const [controls, setControls] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    api.controls().then(setControls).catch((e) => setError(e.message))
  }, [])

  if (error) return <div className="p-6"><ErrorState message={error} /></div>
  if (!controls) return <LoadingState />

  return (
    <div className="p-6 max-w-5xl mx-auto">
      <h1 className="text-xl font-semibold mb-4">Security Controls</h1>
      <Card>
        <div className="overflow-x-auto"><table className="w-full text-sm">
          <thead><tr className="text-left text-slate-400 border-b border-slate-800">
            <th className="py-2">Control</th><th>Type</th><th>Target</th><th>Actual</th><th>Status</th><th>Owner</th>
          </tr></thead>
          <tbody>
            {controls.map((c) => (
              <tr key={c.control_id} className="border-b border-slate-900">
                <td className="py-2">
                  <Link to={`/controls/${c.control_id}`} className="text-blue-400 hover:underline">{c.control_name}</Link>
                </td>
                <td>{c.control_type}</td>
                <td>{c.target_coverage}%</td>
                <td>{c.actual_coverage}%</td>
                <td><StatusBadge text={c.status} tone="good" /></td>
                <td className="text-slate-500">{c.owner}</td>
              </tr>
            ))}
          </tbody>
        </table></div>
      </Card>
    </div>
  )
}
