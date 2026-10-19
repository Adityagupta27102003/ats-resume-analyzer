import { useRef, useState } from 'react'
import { Spinner } from './ui.jsx'

// Mirrors backend/core/config.py so users get instant feedback instead of a round-trip 4xx.
const MAX_FILE_MB = 5
const MIN_JD = 50
const MAX_JD = 20000
const ACCEPTED = ['.pdf', '.docx']

function validateFile(file) {
  const ext = file.name.slice(file.name.lastIndexOf('.')).toLowerCase()
  if (!ACCEPTED.includes(ext)) return 'Please upload a PDF or DOCX file.'
  if (file.size > MAX_FILE_MB * 1024 * 1024) return `File is larger than ${MAX_FILE_MB} MB.`
  if (file.size === 0) return 'This file is empty.'
  return null
}

export default function UploadForm({ onSubmit, loading }) {
  const [file, setFile] = useState(null)
  const [fileError, setFileError] = useState(null)
  const [jd, setJd] = useState('')
  const [dragging, setDragging] = useState(false)
  const inputRef = useRef(null)

  function pickFile(f) {
    if (!f) return
    const err = validateFile(f)
    setFileError(err)
    setFile(err ? null : f)
  }

  const jdLength = jd.trim().length
  const jdValid = jdLength >= MIN_JD && jdLength <= MAX_JD
  const canSubmit = file && jdValid && !loading

  function handleSubmit(e) {
    e.preventDefault()
    if (canSubmit) onSubmit(file, jd.trim())
  }

  return (
    <form onSubmit={handleSubmit} className="grid gap-6 lg:grid-cols-2">
      {/* Resume upload */}
      <div className="flex flex-col">
        <label className="mb-2 text-sm font-semibold text-slate-900">1. Your resume</label>
        <div
          role="button"
          tabIndex={0}
          onClick={() => inputRef.current?.click()}
          onKeyDown={(e) => (e.key === 'Enter' || e.key === ' ') && inputRef.current?.click()}
          onDragOver={(e) => { e.preventDefault(); setDragging(true) }}
          onDragLeave={() => setDragging(false)}
          onDrop={(e) => { e.preventDefault(); setDragging(false); pickFile(e.dataTransfer.files[0]) }}
          className={`flex flex-1 cursor-pointer flex-col items-center justify-center rounded-2xl border-2 border-dashed p-8 text-center transition
            ${dragging ? 'border-indigo-500 bg-indigo-50' : 'border-slate-300 bg-white hover:border-indigo-400 hover:bg-slate-50'}`}
        >
          <svg className="mb-3 h-10 w-10 text-indigo-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 0 0-3.375-3.375h-1.5A1.125 1.125 0 0 1 13.5 7.125v-1.5a3.375 3.375 0 0 0-3.375-3.375H8.25m6.75 12-3-3m0 0-3 3m3-3v6m-1.5-15H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 0 0-9-9Z" />
          </svg>
          {file ? (
            <>
              <p className="font-medium text-slate-900 break-all">{file.name}</p>
              <p className="mt-1 text-xs text-slate-500">{(file.size / 1024).toFixed(0)} KB · click to change</p>
            </>
          ) : (
            <>
              <p className="font-medium text-slate-900">Drop your resume here or click to browse</p>
              <p className="mt-1 text-xs text-slate-500">PDF or DOCX, up to {MAX_FILE_MB} MB</p>
            </>
          )}
          <input
            ref={inputRef}
            type="file"
            accept={ACCEPTED.join(',')}
            className="hidden"
            onChange={(e) => pickFile(e.target.files[0])}
          />
        </div>
        {fileError && <p className="mt-2 text-sm text-rose-600">{fileError}</p>}
      </div>

      {/* Job description */}
      <div className="flex flex-col">
        <label htmlFor="jd" className="mb-2 text-sm font-semibold text-slate-900">2. Job description</label>
        <textarea
          id="jd"
          value={jd}
          onChange={(e) => setJd(e.target.value)}
          placeholder="Paste the full job description, including requirements and responsibilities…"
          className="min-h-64 flex-1 resize-y rounded-2xl border border-slate-300 bg-white p-4 text-sm leading-relaxed shadow-sm outline-none placeholder:text-slate-400 focus:border-indigo-500 focus:ring-2 focus:ring-indigo-200"
        />
        <p className={`mt-2 text-xs ${jdLength > 0 && !jdValid ? 'text-rose-600' : 'text-slate-500'}`}>
          {jdLength.toLocaleString()} characters
          {jdLength > 0 && jdLength < MIN_JD && ` · at least ${MIN_JD} needed`}
          {jdLength > MAX_JD && ` · max ${MAX_JD.toLocaleString()}`}
        </p>
      </div>

      <div className="lg:col-span-2">
        <button
          type="submit"
          disabled={!canSubmit}
          className="inline-flex w-full items-center justify-center gap-2 rounded-xl bg-indigo-600 px-6 py-3 font-semibold text-white shadow-sm transition hover:bg-indigo-700 disabled:cursor-not-allowed disabled:bg-slate-300 sm:w-auto"
        >
          {loading && <Spinner />}
          {loading ? 'Analyzing…' : 'Analyze resume'}
        </button>
      </div>
    </form>
  )
}
