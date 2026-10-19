import { useEffect, useState } from 'react'
import { deleteHistory, getHistory } from '../api.js'
import { Card, Spinner, scoreTone } from './ui.jsx'

const dateFmt = new Intl.DateTimeFormat(undefined, { dateStyle: 'medium', timeStyle: 'short' })

export default function History({ token, onOpen }) {
  const [items, setItems] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    let cancelled = false
    getHistory(token)
      .then((rows) => !cancelled && setItems(rows))
      .catch((err) => !cancelled && setError(err.message))
    return () => { cancelled = true }
  }, [token])

  async function handleDelete(id) {
    if (!window.confirm('Delete this analysis?')) return
    const previous = items
    setItems(items.filter((i) => i.id !== id))   // optimistic: remove now, restore on failure
    try {
      await deleteHistory(id, token)
    } catch (err) {
      setItems(previous)
      setError(err.message)
    }
  }

  if (error) return <Card><p className="text-sm text-rose-600">{error}</p></Card>
  if (!items) return <div className="flex justify-center py-16 text-indigo-600"><Spinner className="h-8 w-8" /></div>

  return (
    <div>
      <h1 className="mb-6 text-2xl font-bold text-slate-900">Your analyses</h1>
      {items.length === 0 ? (
        <Card><p className="text-sm text-slate-600">No saved analyses yet. Run one while signed in and it will show up here.</p></Card>
      ) : (
        <ul className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {items.map((item) => (
            <li key={item.id} className="group relative rounded-2xl border border-slate-200 bg-white shadow-sm transition hover:border-indigo-300 hover:shadow">
              <button onClick={() => onOpen(item.analysis_result)} className="flex w-full items-center gap-4 p-4 text-left">
                <span className={`text-3xl font-bold ${scoreTone(item.ats_score).text}`}>{item.ats_score}</span>
                <span className="min-w-0 flex-1">
                  <span className="block truncate font-semibold text-slate-900">{item.job_title || 'Untitled role'}</span>
                  <span className="block truncate text-xs text-slate-500">{item.filename}</span>
                  <span className="block text-xs text-slate-400">{dateFmt.format(new Date(item.created_at))}</span>
                </span>
              </button>
              <button
                onClick={() => handleDelete(item.id)}
                aria-label="Delete analysis"
                className="absolute top-2 right-2 rounded-lg p-1.5 text-slate-400 opacity-0 transition group-hover:opacity-100 hover:bg-rose-50 hover:text-rose-600 focus:opacity-100"
              >
                <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M6 7h12M9 7V5a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2m-8 0 1 12a1 1 0 0 0 1 1h6a1 1 0 0 0 1-1l1-12" />
                </svg>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
