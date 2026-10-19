import os
from pathlib import Path

# Verify HTTPS against the OS certificate store instead of certifi's bundle. Needed on
# machines where antivirus/corporate proxies re-sign TLS traffic (otherwise model
# downloads, Groq and Supabase calls fail with CERTIFICATE_VERIFY_FAILED).
try:
    import truststore
    truststore.inject_into_ssl()
except ImportError:
    pass

# Load .env from the project root (two levels up from this file) explicitly —
# load_dotenv() with no args relies on caller-frame inspection that can fail
# silently under uvicorn reload, leaving env vars unset.
try:
    from dotenv import load_dotenv
    _ENV_PATH = Path(__file__).resolve().parents[2] / '.env'
    load_dotenv(_ENV_PATH)
except ImportError:
    pass

#api metadata
APP_TITLE='ATS RESUME ANALYZER API'
APP_VERSION='1.0.0'
APP_DESCRIPTION='analyse resumes against job description using nlp + ml'

# Comma-separated list in env, e.g. "http://localhost:5173,https://ats.vercel.app"
# (no trailing slashes — browsers send the Origin header without one)
ALLOWED_ORIGINS = [
    o.strip().rstrip('/')
    for o in os.getenv('ALLOWED_ORIGINS', 'http://localhost:5173').split(',')
    if o.strip()
]

#file
MAX_FILE_SIZE_MB=5
MAX_FILE_SIZE_BYTES=MAX_FILE_SIZE_MB*1024*1024
SUPPORTED_EXTENSIONS = {'.pdf', '.docx'}

MIN_JD_CHARS=50
MAX_JD_CHARS=20000

EMBEDDING_MODEL = os.getenv('EMBEDDING_MODEL', 'sentence-transformers/all-MiniLM-L6-v2')
# Where the ONNX weights are cached; the Docker image bakes them in here.
EMBEDDING_CACHE_DIR = os.getenv('EMBEDDING_CACHE_DIR') or None

# Score component weights (sum = 100) — business logic treated as config
SCORE_WEIGHTS = {
    "keywords": 35,     # hard-skill overlap with the JD
    "semantic": 30,     # BERT embedding similarity to JD requirements
    "content": 20,      # action verbs, quantified impact, bullet density
    "formatting": 15,   # contact info, standard sections, length
}

# Raw cosine similarity from MiniLM rarely goes below ~0.15 (unrelated text)
# or above ~0.75 (near-paraphrase); rescale that band to 0..1.
SEMANTIC_SIM_FLOOR=0.15
SEMANTIC_SIM_CEIL=0.70

SUPABASE_URL       = os.getenv('SUPABASE_URL', '')
SUPABASE_KEY       = os.getenv('SUPABASE_KEY', '')          # secret/service_role — DB writes (bypasses RLS)
SUPABASE_ANON_KEY  = os.getenv('SUPABASE_ANON_KEY', '')     # publishable/anon — used to verify user tokens
GROQ_API_KEY       = os.getenv('GROQ_API_KEY', '')
# Groq retires models regularly (llama-3.3-70b-versatile was removed), so this is overridable.
GROQ_MODEL         = os.getenv('GROQ_MODEL', 'openai/gpt-oss-120b')
