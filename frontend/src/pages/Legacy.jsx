import { useEffect, useState } from 'react'
import { api } from '../services/api'
import { useAuth } from '../hooks/useAuth'
import { Card, KpiCard, LoadingState, ErrorState } from '../components/ui'

const CAN_MODIFY_ROLES = ['management', 'security_engineer']

export default function Legacy() {
  const { user } = useAuth()
  const canModify = CAN_MODIFY_ROLES.includes(user?.role)
  const [status, setStatus] = useState(null)
  const [audit, setAudit] = useState([])
  const [error, setError] = useState(null)
  const [busy, setBusy] = useState(false)
  const [lastAction, setLastAction] = useState(null)

  async function refresh() {
    const [s, a] = await Promise.all([api.legacyStatus(), api.legacyAuditLog()])
    setStatus(s)
    setAudit(a)
  }

  useEffect(() => {
    refresh().catch((e) => setError(e.message))
  }, [])

  async function handleMigrate() {
    setBusy(true)
    try {
      const res = await api.legacyMigrate()
      setLastAction(`Migrated ${res.migrated_count} legacy case(s) into the new platform.`)
      await refresh()
    } catch (e) {
      setError(e.message)
    } finally {
      setBusy(false)
    }
  }

  async function handleVerify() {
    setBusy(true)
    try {
      const res = await api.legacyVerify()
      setLastAction(`Verified ${res.verified_count} migrated case(s).`)
      await refresh()
    } catch (e) {
      setError(e.message)
    } finally {
      setBusy(false)
    }
  }

  async function handleRollback() {
    setBusy(true)
    try {
      const res = await api.legacyRollback('Demonstration rollback triggered from UI')
      setLastAction(`Rolled back ${res.rolled_back_count} case(s) to legacy workflow.`)
      await refresh()
    } catch (e) {
      setError(e.message)
    } finally {
      setBusy(false)
    }
  }

  if (error) return <div className="p-6"><ErrorState message={error} /></div>
  if (!status) return <LoadingState />

  return (
    <div className="p-6 max-w-5xl mx-auto flex flex-col gap-6">
      <h1 className="text-xl font-semibold">Legacy Workflow Coexistence & Rollback</h1>
      <p className="text-sm text-slate-400">
        Legacy SOC cases coexist with the new risk platform during migration. Use the controls below to
        demonstrate migration, verification, and rollback — every transition is written to the audit log.
      </p>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <KpiCard label="Not Migrated" value={status.not_migrated} />
        <KpiCard label="Migrated" value={status.migrated} />
        <KpiCard label="Verified" value={status.verified} />
        <KpiCard label="Rolled Back" value={status.rolled_back} />
      </div>

      <Card title="Migration Controls (demo)">
        {!canModify && (
          <p className="text-sm text-yellow-400 mb-3">
            Your role ({user?.role.replace('_', ' ')}) has read-only access to legacy migration. Only
            Management and Security Engineer accounts can trigger migrate/verify/rollback — this is
            enforced by the backend, not just hidden here.
          </p>
        )}
        <div className="flex gap-3 flex-wrap">
          <button disabled={busy || !canModify} onClick={handleMigrate}
            className="bg-blue-600 hover:bg-blue-500 disabled:opacity-40 disabled:cursor-not-allowed rounded px-4 py-2 text-sm font-medium">
            Migrate NOT_MIGRATED cases
          </button>
          <button disabled={busy || !canModify} onClick={handleVerify}
            className="bg-green-700 hover:bg-green-600 disabled:opacity-40 disabled:cursor-not-allowed rounded px-4 py-2 text-sm font-medium">
            Verify MIGRATED cases
          </button>
          <button disabled={busy || !canModify} onClick={handleRollback}
            className="bg-red-700 hover:bg-red-600 disabled:opacity-40 disabled:cursor-not-allowed rounded px-4 py-2 text-sm font-medium">
            Rollback to legacy workflow
          </button>
        </div>
        {lastAction && <p className="text-sm text-slate-400 mt-3">{lastAction}</p>}
      </Card>

      <Card title="Audit Log">
        <div className="overflow-x-auto"><table className="w-full text-sm">
          <thead><tr className="text-left text-slate-400 border-b border-slate-800">
            <th className="py-2">Action</th><th>Entity</th><th>Previous</th><th>New</th><th>Timestamp</th><th>Detail</th>
          </tr></thead>
          <tbody>
            {audit.map((a) => (
              <tr key={a.audit_id} className="border-b border-slate-900">
                <td className="py-2">{a.action}</td>
                <td className="text-slate-500">{a.entity_id}</td>
                <td>{a.previous_state}</td>
                <td>{a.new_state}</td>
                <td className="text-slate-500">{new Date(a.timestamp).toLocaleString()}</td>
                <td className="text-slate-400">{a.detail}</td>
              </tr>
            ))}
          </tbody>
        </table></div>
      </Card>
    </div>
  )
}
