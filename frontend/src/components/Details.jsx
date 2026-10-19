import { Card, Chip, ProgressBar, scoreTone } from './ui.jsx'

const PRIORITY_STYLES = {
  high: 'bg-rose-100 text-rose-700',
  medium: 'bg-amber-100 text-amber-700',
  low: 'bg-slate-100 text-slate-600',
}

export function Suggestions({ items }) {
  if (!items.length) {
    return <Card title="Suggestions"><p className="text-sm text-slate-600">No major issues found — nice work.</p></Card>
  }
  return (
    <Card title="Suggestions" subtitle="Highest-impact fixes first">
      <ul className="space-y-3">
        {items.map((s, i) => (
          <li key={i} className="flex gap-3">
            <span className={`mt-0.5 h-fit shrink-0 rounded-md px-2 py-0.5 text-[11px] font-semibold uppercase tracking-wide ${PRIORITY_STYLES[s.priority]}`}>
              {s.priority}
            </span>
            <p className="text-sm leading-relaxed text-slate-700">{s.message}</p>
          </li>
        ))}
      </ul>
    </Card>
  )
}

function ChipGroup({ label, items, variant }) {
  if (!items.length) return null
  return (
    <div>
      <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">{label} ({items.length})</h3>
      <div className="flex flex-wrap gap-1.5">
        {items.map((k) => <Chip key={k} variant={variant}>{k}</Chip>)}
      </div>
    </div>
  )
}

export function Keywords({ result }) {
  const { matched_keywords, missing_keywords, missing_preferred, keyword_match } = result
  const hasJdSkills = 'keywords' in result.breakdown
  return (
    <Card
      title="Keywords"
      subtitle={hasJdSkills ? `${Math.round(keyword_match)}% of weighted JD skills found` : 'No recognisable hard skills in this job description'}
    >
      <div className="space-y-4">
        <ChipGroup label="Missing — required" items={missing_keywords} variant="missing" />
        <ChipGroup label="Missing — nice to have" items={missing_preferred} variant="preferred" />
        <ChipGroup label="Matched" items={matched_keywords} variant="matched" />
        {!hasJdSkills && <ChipGroup label="Skills in your resume" items={result.resume_skills} variant="neutral" />}
      </div>
    </Card>
  )
}

export function Requirements({ semantic }) {
  return (
    <Card
      title="Requirement coverage"
      subtitle="Each JD requirement paired with the closest line in your resume (weakest first)"
    >
      <ul className="divide-y divide-slate-100">
        {semantic.requirements.map((r, i) => (
          <li key={i} className="py-3 first:pt-0 last:pb-0">
            <div className="flex items-start justify-between gap-4">
              <p className="text-sm font-medium text-slate-800">{r.requirement}</p>
              <span className={`shrink-0 text-sm font-semibold ${scoreTone(r.similarity).text}`}>{Math.round(r.similarity)}%</span>
            </div>
            <ProgressBar value={r.similarity} className="my-2 h-1.5" />
            <p className="text-xs text-slate-500">
              <span className="font-medium text-slate-600">Closest match:</span> {r.best_match}
            </p>
          </li>
        ))}
      </ul>
    </Card>
  )
}

function Check({ ok, children }) {
  return (
    <li className="flex items-center gap-2 text-sm">
      <span className={`flex h-5 w-5 shrink-0 items-center justify-center rounded-full text-xs font-bold ${ok ? 'bg-emerald-100 text-emerald-700' : 'bg-rose-100 text-rose-700'}`}>
        {ok ? '✓' : '✕'}
      </span>
      <span className={ok ? 'text-slate-700' : 'text-slate-500'}>{children}</span>
    </li>
  )
}

function Stat({ value, label }) {
  return (
    <div className="rounded-xl bg-slate-50 p-3 text-center">
      <div className="text-xl font-bold text-slate-900">{value}</div>
      <div className="text-xs text-slate-500">{label}</div>
    </div>
  )
}

export function ResumeChecks({ content, formatting }) {
  const { contact } = formatting
  const sections = ['experience', 'education', 'skills', 'projects']
  return (
    <Card title="Resume checks">
      <div className="grid grid-cols-3 gap-2">
        <Stat value={content.bullet_count} label="bullets" />
        <Stat value={`${Math.round(content.action_verb_ratio)}%`} label="action verbs" />
        <Stat value={content.quantified_bullets} label="quantified" />
      </div>
      <div className="mt-5 grid gap-5 sm:grid-cols-2">
        <div>
          <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">Contact</h3>
          <ul className="space-y-1.5">
            <Check ok={contact.email}>Email</Check>
            <Check ok={contact.phone}>Phone</Check>
            <Check ok={contact.linkedin}>LinkedIn</Check>
            <Check ok={contact.github}>GitHub</Check>
          </ul>
        </div>
        <div>
          <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">Sections</h3>
          <ul className="space-y-1.5">
            {sections.map((s) => (
              <Check key={s} ok={formatting.sections_found.includes(s)}>
                <span className="capitalize">{s}</span>
              </Check>
            ))}
          </ul>
        </div>
      </div>
      <p className="mt-5 text-xs text-slate-500">
        {formatting.word_count} words
        {content.weak_phrases.length > 0 && <> · weak phrases: {content.weak_phrases.map((p) => `“${p}”`).join(', ')}</>}
      </p>
    </Card>
  )
}
