const API_URL = (import.meta.env.VITE_API_URL || '').replace(/\/$/, '')

// FastAPI errors come back as {detail: "message"} for HTTPException, or
// {detail: [{msg, loc}, ...]} for request-validation errors.
function errorMessage(body, status) {
  const detail = body?.detail
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail) && detail.length) return detail.map((d) => d.msg).join('; ')
  return `Request failed (${status})`
}

async function request(path, { method = 'GET', body, token, signal } = {}) {
  let resp
  try {
    resp = await fetch(`${API_URL}/api/v1${path}`, {
      method,
      body,
      headers: token ? { Authorization: `Bearer ${token}` } : {},
      signal,
    })
  } catch (err) {
    if (err.name === 'AbortError') throw err
    // The free HF Space sleeps when idle; the first request after that can fail or take ~1 min.
    throw new Error('Could not reach the server. It may be waking up — try again in a few seconds.')
  }

  if (resp.status === 204) return null
  const data = await resp.json().catch(() => null)
  if (!resp.ok) throw new Error(errorMessage(data, resp.status))
  return data
}

export function analyzeResume(file, jobDescription, { token, signal } = {}) {
  const form = new FormData()
  form.append('file', file)
  form.append('job_description', jobDescription)
  return request('/analyze-resume', { method: 'POST', body: form, token, signal })
}

export const getHistory = (token) => request('/history', { token })

export const deleteHistory = (id, token) =>
  request(`/history/${encodeURIComponent(id)}`, { method: 'DELETE', token })
