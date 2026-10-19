import { useEffect, useState } from 'react'
import { createClient } from '@supabase/supabase-js'

const url = import.meta.env.VITE_SUPABASE_URL
const key = import.meta.env.VITE_SUPABASE_ANON_KEY   // publishable/anon key — safe in the browser (RLS protects data)

// Auth is optional: without these env vars the app still works, just without login/history.
export const supabase = url && key ? createClient(url, key) : null

export function useSession() {
  const [session, setSession] = useState(null)

  useEffect(() => {
    if (!supabase) return
    supabase.auth.getSession().then(({ data }) => setSession(data.session))
    // Fires on sign-in, sign-out and silent token refresh, so the token we send is always current.
    const { data } = supabase.auth.onAuthStateChange((_event, s) => setSession(s))
    return () => data.subscription.unsubscribe()
  }, [])

  return session
}
