import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.core.config import(
    ALLOWED_ORIGINS,
    APP_DESCRIPTION,
    APP_TITLE,
    APP_VERSION,
    SPACY_MODEL,
    SENTENCE_TRANSFORMER_MODEL
)
from backend.api.routes import router
import backend.utils.file_utils  # noqa: F401 — configures the app logger

logger=logging.getLogger('ats_resume_scorer')

@asynccontextmanager
async def lifespan(app:FastAPI):
    # Models are loaded once at startup (a few seconds) instead of per request.
    logger.info('Starting ATS Resume Analyzer API...')

    import spacy
    from sentence_transformers import SentenceTransformer
    from backend.services.scorer import ATSScorer

    logger.info(f'Loading spaCy model: {SPACY_MODEL}')
    nlp = spacy.load(SPACY_MODEL, disable=['parser', 'ner', 'lemmatizer'])

    logger.info(f'Loading SentenceTransformer: {SENTENCE_TRANSFORMER_MODEL}')
    embedder = SentenceTransformer(SENTENCE_TRANSFORMER_MODEL, device='cpu')

    app.state.scorer = ATSScorer(nlp, embedder)
    logger.info('All models loaded. API is ready to serve requests.')

    yield

    logger.info('Shutting down the API')

app=FastAPI(
    title=APP_TITLE,
    description=APP_DESCRIPTION,
    version=APP_VERSION,
    lifespan=lifespan,
    docs_url='/docs',
    redoc_url='/redoc'
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods     = ['*'],
    allow_headers     = ['*'],
)

app.include_router(router)

@app.get('/')
async def root():
    return {
        'name':      APP_TITLE,
        'version':   APP_VERSION,
        'docs':      '/docs',
        'endpoints': {
            'POST   /api/v1/analyze-resume': 'Analyze a resume against a job description',
            'GET    /api/v1/history':        'Get user history (auth)',
            'DELETE /api/v1/history/:id':    'Delete a history entry (auth)',
            'GET    /api/v1/health':         'Health check',
        },
    }

if __name__=='__main__':
    import uvicorn
    uvicorn.run(
        'backend.main:app',
        host    = '0.0.0.0',
        port    = 8000,
        reload  = True,    # Auto-restart on code changes (dev only)
    )
