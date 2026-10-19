import { Card, ProgressBar, scoreTone } from './ui.jsx'

const COMPONENTS = {
  keywords: { label: 'Keyword match', hint: 'Hard skills from the JD found in your resume' },
  semantic: { label: 'Semantic relevance', hint: 'How closely your experience matches JD requirements (BERT embeddings)' },
  content: { label: 'Content quality', hint: 'Action verbs, quantified impact, no weak phrases' },
  formatting: { label: 'Formatting', hint: 'Contact info, standard sections, length' },
}

function ScoreRing({ score, label }) {
  const r = 52
  const circumference = 2 * Math.PI * r
  const tone = scoreTone(score)
  return (
    <div className="relative h-40 w-40 shrink-0">
      <svg viewBox="0 0 120 120" className="h-full w-full -rotate-90">
        <circle cx="60" cy="60" r={r} fill="none" stroke="#e2e8f0" strokeWidth="10" />
        <circle
          cx="60" cy="60" r={r} fill="none" stroke={tone.stroke} strokeWidth="10" strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={circumference * (1 - score / 100)}
          className="transition-[stroke-dashoffset] duration-1000"
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className={`text-4xl font-bold ${tone.text}`}>{score}</span>
        <span className="text-xs font-medium text-slate-500">{label}</span>
      </div>
    </div>
  )
}

export default function ScoreSummary({ result }) {
  return (
    <Card>
      <div className="flex flex-col items-center gap-6 sm:flex-row sm:items-start">
        <ScoreRing score={result.ats_score} label={result.score_label} />
        <div className="w-full flex-1">
          <h2 className="text-lg font-semibold text-slate-900">
            {result.job_title}
          </h2>
          <p className="mb-4 text-sm text-slate-500">
            {result.candidate_name ? `${result.candidate_name} · ` : ''}{result.filename}
          </p>
          <ul className="space-y-3">
            {Object.entries(result.breakdown).map(([key, { score, weight }]) => (
              <li key={key} title={COMPONENTS[key]?.hint}>
                <div className="mb-1 flex items-baseline justify-between text-sm">
                  <span className="font-medium text-slate-700">
                    {COMPONENTS[key]?.label ?? key}
                    <span className="ml-1.5 text-xs font-normal text-slate-400">{Math.round(weight)}% weight</span>
                  </span>
                  <span className={`font-semibold ${scoreTone(score).text}`}>{Math.round(score)}</span>
                </div>
                <ProgressBar value={score} />
              </li>
            ))}
          </ul>
        </div>
      </div>
    </Card>
  )
}
