-- Run once in the Supabase SQL editor.
create table if not exists public.analyses (
    id               uuid primary key default gen_random_uuid(),
    user_id          uuid not null references auth.users(id) on delete cascade,
    filename         text not null,
    job_title        text,
    ats_score        integer not null,
    keyword_match    real,
    missing_keywords jsonb default '[]'::jsonb,
    analysis_result  jsonb not null,
    created_at       timestamptz not null default now()
);

create index if not exists analyses_user_created_idx
    on public.analyses (user_id, created_at desc);

-- The backend writes with the secret key (bypasses RLS). RLS stays on so the
-- publishable/anon key in the browser can never read other users' rows.
alter table public.analyses enable row level security;

drop policy if exists "users read own analyses" on public.analyses;
create policy "users read own analyses" on public.analyses
    for select using (auth.uid() = user_id);
