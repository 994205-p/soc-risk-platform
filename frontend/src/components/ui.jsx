export function KpiCard({ label, value, sub }) {
  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 flex flex-col gap-1 hover:border-slate-700 transition-colors">
      <span className="text-xs uppercase tracking-wide text-slate-400">{label}</span>
      <span className="text-2xl font-semibold text-slate-100">{value}</span>
      {sub && <span className="text-xs text-slate-500">{sub}</span>}
    </div>
  )
}

const BAND_COLORS = {
  VERY_LOW: 'bg-green-600',
  LOW: 'bg-lime-600',
  MODERATE: 'bg-yellow-500 text-slate-900',
  HIGH: 'bg-orange-600',
  CRITICAL: 'bg-red-600',
}

export function RiskBadge({ band, score }) {
  const cls = BAND_COLORS[band] || 'bg-slate-600'
  return (
    <span className={`inline-flex items-center gap-2 px-3 py-1 rounded-full text-sm font-medium ${cls}`}>
      {score != null ? `${score}/100` : 'N/A'} · {band ? band.replace('_', ' ') : 'UNKNOWN'}
    </span>
  )
}

// Meaningful color mapping per spec: green=healthy, yellow=warning,
// orange=high risk/aging, red=critical/invalid, gray=unknown.
const FRESHNESS_COLORS = {
  FRESH: 'text-green-400',
  AGING: 'text-yellow-400',
  STALE: 'text-orange-400',
  MISSING: 'text-red-400',
  INVALID: 'text-red-500',
  FALLBACK: 'text-red-400',
}

const FRESHNESS_TITLES = {
  FRESH: 'Data is up to date',
  AGING: 'Data is getting old — still usable but worth refreshing soon',
  STALE: 'Data is old — confidence in results using this data is reduced',
  MISSING: 'No data available for this source',
  INVALID: 'Timestamp is logically impossible (e.g. in the future) — likely a data defect',
  FALLBACK: 'Showing the last verified snapshot because fresh data was unavailable',
}

export function FreshnessBadge({ status }) {
  return (
    <span
      className={`text-xs font-semibold ${FRESHNESS_COLORS[status] || 'text-slate-400'}`}
      title={FRESHNESS_TITLES[status] || 'Unknown data freshness'}
    >
      ● {status || 'UNKNOWN'}
    </span>
  )
}

export function StatusBadge({ text, tone = 'default' }) {
  const tones = {
    default: 'bg-slate-700 text-slate-200',
    good: 'bg-green-900 text-green-300',
    warn: 'bg-yellow-900 text-yellow-300',
    bad: 'bg-red-900 text-red-300',
  }
  return <span className={`px-2 py-0.5 rounded text-xs font-medium whitespace-nowrap ${tones[tone]}`}>{text}</span>
}

// Distinguishes AI-assisted explanations from the deterministic fallback --
// per docs/responsible_ai.md this label must never be hidden from the user.
export function ExplanationLabel({ source, label }) {
  if (!label) return null
  const isAi = source === 'ai_assisted'
  return (
    <span
      className={`text-xs px-2 py-0.5 rounded-full border ${
        isAi ? 'border-purple-700 text-purple-300 bg-purple-950' : 'border-slate-700 text-slate-400 bg-slate-800'
      }`}
      title={isAi
        ? 'Reworded by an AI model, grounded strictly in the deterministic evidence below.'
        : 'Generated entirely by the deterministic, rule-based risk engine — no AI involved.'}
    >
      {isAi ? '✨ ' : ''}{label}
    </span>
  )
}

export function Card({ title, children, right }) {
  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-4">
      {(title || right) && (
        <div className="flex items-center justify-between mb-3 flex-wrap gap-2">
          {title && <h3 className="text-sm font-semibold text-slate-300">{title}</h3>}
          {right}
        </div>
      )}
      {children}
    </div>
  )
}

export function LoadingState({ label = 'Loading…' }) {
  return (
    <div className="text-slate-500 text-sm py-10 text-center flex flex-col items-center gap-2">
      <div className="w-5 h-5 border-2 border-slate-700 border-t-blue-500 rounded-full animate-spin" />
      {label}
    </div>
  )
}

export function ErrorState({ message }) {
  return (
    <div className="bg-red-950 border border-red-800 text-red-300 text-sm rounded-lg p-3">
      Error: {message}
    </div>
  )
}

export function EmptyState({ message = 'Nothing to show here yet.' }) {
  return (
    <div className="text-slate-500 text-sm py-8 text-center border border-dashed border-slate-800 rounded-lg">
      {message}
    </div>
  )
}
