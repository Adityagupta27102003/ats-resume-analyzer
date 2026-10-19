# ATS Resume Analyzer

Score a resume against a job description the way an Applicant Tracking System would, and get specific, prioritised fixes.

**Live demo:** [ats-resume-analyzer-flax-mu.vercel.app](https://ats-resume-analyzer-flax-mu.vercel.app) · **API docs:** [ats-resume-api-p2fx.onrender.com/docs](https://ats-resume-api-p2fx.onrender.com/docs)

> The API runs on Render's free tier and sleeps when idle. The first request after a while can take ~1 minute to wake it up.

![Python](https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)
![React](https://img.shields.io/badge/React-19-61DAFB?logo=react&logoColor=black)
[![tests](https://github.com/Adityagupta27102003/ats-resume-analyzer/actions/workflows/tests.yml/badge.svg)](https://github.com/Adityagupta27102003/ats-resume-analyzer/actions/workflows/tests.yml)

## What it does

Upload a PDF/DOCX resume and paste a job description. The analyzer returns:

- **An ATS score (0–100)** made of four weighted components
- **Missing keywords**: required vs. nice-to-have skills from the JD that the resume lacks
- **Requirement coverage**: each JD requirement paired with the closest line in the resume, found with BERT sentence embeddings
- **Prioritised suggestions**: missing skills, unquantified bullets, weak phrases ("responsible for"), missing sections or contact info
- **History** (optional login): past analyses saved per user

## How the score works

| Component | Weight | How it's computed |
|---|---|---|
| Keywords | 35% | Hard skills in the JD vs. the resume. Required skills count double. Matching handles aliases (`k8s` → Kubernetes, `ReactJS` → React) via a curated skill vocabulary + spaCy `PhraseMatcher`, then fuzzy matching (rapidfuzz) for variants like "RESTful APIs". |
| Semantic | 30% | Each JD requirement and each resume line is embedded with **all-MiniLM-L6-v2** (a distilled BERT sentence-transformer, run on ONNX Runtime). For every requirement, the best cosine similarity across resume lines is taken, then rescaled from the model's practical range (0.15–0.70) to 0–1. |
| Content | 20% | Share of bullets starting with strong action verbs, number of quantified bullets (%, $, 10k…), penalty for weak phrases. |
| Formatting | 15% | Email + phone, LinkedIn/GitHub, standard section headings (Experience, Education, Skills, Projects), word count in the 350–1100 range. |

If a JD contains no recognisable hard skills, the keyword component is dropped and its weight is redistributed proportionally, so the score stays on a 0–100 scale.

**LLM parsing with a local fallback.** When a Groq API key is set, an LLM (`openai/gpt-oss-120b` on Groq, configurable via `GROQ_MODEL`) extracts structured data (required vs. preferred skills, responsibilities, job title) from both documents in parallel, using JSON mode with one retry. If Groq is down or rate-limited, every step falls back to local spaCy/regex extraction, so an LLM outage never breaks an analysis. The response says which parser was used.

## Architecture

```mermaid
flowchart LR
    U[React + Vite<br/>Vercel] -->|multipart upload + JWT| A[FastAPI<br/>Render · Docker]
    U -->|email/password login| S[(Supabase Auth)]
    A --> P[pdfplumber / PyPDF2<br/>python-docx]
    A --> G[Groq LLM<br/>structured parsing]
    A --> M[spaCy + MiniLM<br/>scoring engine]
    A -->|verify token, save/read history| DB[(Supabase Postgres<br/>RLS enabled)]
```

**Design decisions**

- **Models load once at startup** (FastAPI lifespan), not per request. Scoring runs in a thread pool so CPU-bound embedding work never blocks the event loop.
- **Files are validated by magic bytes**, not just extension, so a renamed `.exe` → `.pdf` is rejected. Uploads are read with a size cap so oversized files are never fully buffered.
- **Auth tokens are verified by Supabase itself** (`/auth/v1/user`). This works with both legacy HS256 and newer asymmetric signing keys, so the backend never handles the JWT secret.
- **The secret key stays server-side.** The browser only holds the publishable key, and row-level security stops it from reading other users' rows.
- **Errors are typed.** Validation/parsing errors carry a user-safe message (422). Anything unexpected is logged and returned as a generic 500, so internals never leak.
- **BERT on ONNX Runtime instead of PyTorch.** The same MiniLM weights produce identical embeddings (cosine 1.0 against sentence-transformers), but the API runs in ~330 MB of RAM instead of ~1 GB, and the image drops PyTorch entirely. That's what lets it run on a 512 MB free instance. The weights are baked into the Docker image, so cold starts don't download anything.
- **spaCy is used only for tokenization + `PhraseMatcher`**, so a blank English pipeline is loaded instead of `en_core_web_sm`. That's ~50 MB less of models the scorer never uses.

## Tech stack

**Backend:** FastAPI, Pydantic v2, spaCy, MiniLM via fastembed / ONNX Runtime, rapidfuzz, pdfplumber, python-docx, Groq, httpx
**Frontend:** React 19, Vite, Tailwind CSS v4, supabase-js
**Infra:** Docker, Render, Vercel, Supabase (Auth + Postgres), GitHub Actions CI

## Run locally

Requires Python 3.11 and Node 20+.

```bash
# Backend
pip install -r requirements-dev.txt
cp .env.example .env              # all keys optional for local dev
uvicorn backend.main:app --reload # http://localhost:8000/docs

# Frontend (new terminal)
cd frontend
npm install
cp .env.example .env              # optional: Supabase keys enable login/history
npm run dev                       # http://localhost:5173
```

Without a Groq key the analyzer uses local parsing. Without Supabase, login and history are hidden.

**Database (optional):** create a Supabase project and run [`backend/database/schema.sql`](backend/database/schema.sql) in the SQL editor.

**Docker:**

```bash
docker build -t ats-backend .
docker run -p 8000:8000 -e PORT=8000 --env-file .env ats-backend
```

## Tests

```bash
pytest     # 46 tests, ~2 s
```

Tests never load the real models: a blank spaCy tokenizer and a deterministic bag-of-words embedder exercise the same scoring code in milliseconds. API tests run through FastAPI's `TestClient` without triggering the lifespan, so responses are still validated against the Pydantic response models. That catches any drift between scorer output and the API schema. Groq and Supabase are mocked, including the failure paths.

## API

| Method | Path | Auth | Description |
|---|---|---|---|
| `POST` | `/api/v1/analyze-resume` | optional | `multipart/form-data`: `file` (PDF/DOCX ≤ 5 MB), `job_description` (50–20,000 chars). Saved to history if authenticated. |
| `GET` | `/api/v1/history` | required | Last 50 analyses for the user |
| `DELETE` | `/api/v1/history/{id}` | required | Delete one of the user's analyses |
| `GET` | `/api/v1/health` | — | Model / Groq / database status |

## Project structure

```
backend/
  api/routes.py           HTTP endpoints, validation, LLM fallback orchestration
  core/                   config (weights, limits), Supabase token verification
  services/scorer.py      scoring engine (keywords, semantic, content, formatting)
  services/skills.py      curated skill vocabulary + aliases, action verbs
  services/groq_parser.py LLM structured extraction (JSON mode + retry)
  services/resume_parser.py PDF/DOCX text extraction with fallback
  database/               Supabase REST client, SQL schema
frontend/src/
  App.jsx                 views: analyze / results / history
  components/             upload form, score summary, details, history, auth
tests/                    pytest suite (scorer, parsers, API)
Dockerfile                backend image (no PyTorch, model weights baked in)
render.yaml               Render Blueprint for the API
```
