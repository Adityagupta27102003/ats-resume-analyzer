import { useEffect, useRef, useState } from 'react'
import { analyzeResume } from './api.js'
import { supabase, useSession } from './supabase.js'
import UploadForm from './components/UploadForm.jsx'
import ScoreSummary from './components/ScoreSummary.jsx'
import History from './components/History.jsx'
import AuthModal from './components/AuthModal.jsx'
import { Keywords, Requirements, ResumeChecks, Suggestions } from './components/Details.jsx'

const REPO_URL = 'https://github.com/Adityagupta27102003/ats-resume-analyzer'

function Results({ result }) {
  return (
    <div className="grid gap-6 lg:grid-cols-5">
      <div className="space-y-6 lg:col-span-3">
        <ScoreSummary result={result} />
        <Suggestions items={result.suggestions} />
        <Requirements semantic={result.semantic} />
      </div>
      <div className="space-y-6 lg:col-span-2">
        <Keywords result={result} />
        <ResumeChecks content={result.content} formatting={result.formatting} />
      </div>
    </div>
  )
}

export default function App() {
  const session = useSession()
  const token = session?.access_token
  const [view, setView] = useState('analyze')   // 'analyze' | 'result' | 'history'
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [showAuth, setShowAuth] = useState(false)
  const abortRef = useRef(null)

  // Cancel an in-flight request if the component unmounts.
  useEffect(() => () => abortRef.current?.abort(), [])

  // Signing out while on the history page would leave a page that can't load.
  useEffect(() => {
    if (!session && view === 'history') setView('analyze')
  }, [session, view])

  async function handleAnalyze(file, jd) {
    abortRef.current?.abort()
    abortRef.current = new AbortController()
    setLoading(true)
    setError(null)
    try {
      setResult(await analyzeResume(file, jd, { token, signal: abortRef.current.signal }))
      setView('result')
      window.scrollTo({ top: 0, behavior: 'smooth' })
    } catch (err) {
      if (err.name !== 'AbortError') setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  function openFromHistory(analysis) {
    setResult(analysis)
    setView('result')
    window.scrollTo({ top: 0 })
  }

  const navBtn = 'rounded-lg px-3 py-1.5 text-sm font-medium transition'

  return (
    <div className="flex min-h-screen flex-col">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-6xl items-center justify-between gap-2 px-4 py-3 sm:px-6">
          <button onClick={() => setView('analyze')} className="flex items-center gap-2.5">
            <img src="/favicon.svg" alt="" className="h-8 w-8" />
            <span className="text-base font-bold text-slate-900 sm:text-lg">ATS Resume Analyzer</span>
          </button>
          <nav className="flex items-center gap-1">
            {view !== 'analyze' && (
              <button onClick={() => setView('analyze')} className={`${navBtn} text-indigo-600 hover:bg-indigo-50`}>
                New analysis
              </button>
            )}
            {supabase && session && (
              <>
                <button
                  onClick={() => setView('history')}
                  className={`${navBtn} ${view === 'history' ? 'bg-slate-100 text-slate-900' : 'text-slate-600 hover:bg-slate-100'}`}
                >
                  History
                </button>
                <button onClick={() => supabase.auth.signOut()} className={`${navBtn} text-slate-600 hover:bg-slate-100`}>
                  Sign out
                </button>
              </>
            )}
            {supabase && !session && (
              <button onClick={() => setShowAuth(true)} className={`${navBtn} bg-indigo-600 text-white hover:bg-indigo-700`}>
                Sign in
              </button>
            )}
          </nav>
        </div>
      </header>

      <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-8 sm:px-6 sm:py-10">
        {/* The form stays mounted (just hidden) on other views, so "New analysis"
            keeps the pasted JD — handy for re-checking a revised resume. */}
        <div className={view === 'analyze' ? '' : 'hidden'}>
          <div className="mb-8 max-w-2xl">
            <h1 className="text-3xl font-bold tracking-tight text-slate-900 sm:text-4xl">
              See your resume the way an ATS does
            </h1>
            <p className="mt-3 text-slate-600">
              Upload your resume and paste a job description. You'll get a match score, the keywords
              you're missing, and specific fixes — scored with NLP and BERT sentence embeddings.
            </p>
            {supabase && !session && (
              <p className="mt-2 text-sm text-slate-500">
                <button onClick={() => setShowAuth(true)} className="font-medium text-indigo-600 hover:underline">Sign in</button>
                {' '}to save your results and track improvements.
              </p>
            )}
          </div>
          {error && (
            <div role="alert" className="mb-6 rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
              {error}
            </div>
          )}
          <UploadForm onSubmit={handleAnalyze} loading={loading} />
          {loading && (
            <p className="mt-4 text-sm text-slate-500">
              Parsing your resume and comparing it against the job description. This usually takes a few seconds
              (up to a minute if the server was asleep).
            </p>
          )}
        </div>

        {view === 'result' && result && <Results result={result} />}
        {view === 'history' && token && <History token={token} onOpen={openFromHistory} />}
      </main>

      <footer className="border-t border-slate-200 py-5 text-center text-xs text-slate-500">
        FastAPI · spaCy · Sentence-BERT · Groq · Supabase · React —{' '}
        <a href={REPO_URL} target="_blank" rel="noreferrer" className="font-medium text-indigo-600 hover:underline">source on GitHub</a>
      </footer>

      {showAuth && <AuthModal onClose={() => setShowAuth(false)} />}
    </div>
  )
}
