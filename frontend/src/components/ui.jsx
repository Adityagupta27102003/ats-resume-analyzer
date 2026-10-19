// Small shared building blocks + the score → colour mapping used across the results page.
// Thresholds match the backend's score labels (Excellent ≥80, Good ≥65, Fair ≥50).

export function scoreTone(score) {
  if (score >= 80) return { text: 'text-emerald-600', bar: 'bg-emerald-500', stroke: '#10b981' }
  if (score >= 65) return { text: 'text-sky-600', bar: 'bg-sky-500', stroke: '#0ea5e9' }
  if (score >= 50) return { text: 'text-amber-600', bar: 'bg-amber-500', stroke: '#f59e0b' }
  return { text: 'text-rose-600', bar: 'bg-rose-500', stroke: '#f43f5e' }
}

export function Card({ title, subtitle, children, className = '' }) {
  return (
    <section className={`rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6 ${className}`}>
      {title && (
        <header className="mb-4">
          <h2 className="text-base font-semibold text-slate-900">{title}</h2>
          {subtitle && <p className="mt-0.5 text-sm text-slate-500">{subtitle}</p>}
        </header>
      )}
      {children}
    </section>
  )
}

export function ProgressBar({ value, className = '' }) {
  return (
    <div className={`h-2 w-full overflow-hidden rounded-full bg-slate-100 ${className}`}>
      <div
        className={`h-full rounded-full transition-[width] duration-700 ${scoreTone(value).bar}`}
        style={{ width: `${Math.max(2, value)}%` }}
      />
    </div>
  )
}

const CHIP_STYLES = {
  matched: 'bg-emerald-50 text-emerald-700 ring-emerald-200',
  missing: 'bg-rose-50 text-rose-700 ring-rose-200',
  preferred: 'bg-amber-50 text-amber-700 ring-amber-200',
  neutral: 'bg-slate-100 text-slate-700 ring-slate-200',
}

export function Chip({ children, variant = 'neutral' }) {
  return (
    <span className={`inline-flex items-center rounded-full px-2.5 py-1 text-xs font-medium ring-1 ring-inset ${CHIP_STYLES[variant]}`}>
      {children}
    </span>
  )
}

export function Spinner({ className = 'h-5 w-5' }) {
  return (
    <svg className={`animate-spin ${className}`} viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <circle cx="12" cy="12" r="10" stroke="currentColor" strokeOpacity="0.25" strokeWidth="4" />
      <path d="M22 12a10 10 0 0 0-10-10" stroke="currentColor" strokeWidth="4" strokeLinecap="round" />
    </svg>
  )
}
