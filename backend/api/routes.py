import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status
from fastapi.concurrency import run_in_threadpool

from backend.core.auth import get_current_user, get_optional_user
from backend.core.config import MAX_FILE_SIZE_BYTES, MAX_FILE_SIZE_MB, MIN_JD_CHARS, MAX_JD_CHARS
from backend.database import supabase_db
from backend.models.schema import AnalysisResponse, HealthResponse, HistoryItem
from backend.services import groq_parser
from backend.services.resume_parser import parse_resume_file
from backend.utils.file_utils import ATSBaseError, log_error

logger = logging.getLogger('ats_resume_scorer')
router = APIRouter(prefix='/api/v1')


def _llm_parse(resume_text: str, jd_text: str) -> tuple[Optional[dict], Optional[dict]]:
    """Parse resume and JD with Groq in parallel. Any failure → (None, None) and the
    scorer falls back to local extraction, so an LLM outage never breaks analysis."""
    if not groq_parser.is_available():
        return None, None
    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            resume_future = pool.submit(groq_parser.parse_resume, resume_text)
            jd_future = pool.submit(groq_parser.parse_job_description, jd_text)
            return resume_future.result(), jd_future.result()
    except Exception as exc:
        log_error(exc, context='groq_parse (falling back to local parsing)')
        return None, None


def _guess_job_title(jd_text: str) -> str:
    """Without the LLM, JDs usually start with the title as a short first line."""
    first = jd_text.strip().splitlines()[0].strip()
    return first if len(first.split()) <= 10 else 'Untitled role'


def _run_analysis(scorer, file_data: bytes, filename: str, jd_text: str) -> dict:
    resume_text, _ = parse_resume_file(file_data, filename)
    resume_parsed, jd_parsed = _llm_parse(resume_text, jd_text)

    result = scorer.analyze(resume_text, jd_text, resume_parsed, jd_parsed)
    result['filename'] = filename
    result['parser'] = 'groq' if jd_parsed else 'local'
    result['job_title'] = (jd_parsed or {}).get('job_title') or _guess_job_title(jd_text)
    result['candidate_name'] = (resume_parsed or {}).get('name') or None
    return result


@router.get('/health', response_model=HealthResponse)
async def health(request: Request):
    return HealthResponse(
        status='ok',
        models_loaded=hasattr(request.app.state, 'scorer'),
        groq_enabled=groq_parser.is_available(),
        database_enabled=supabase_db.is_enabled(),
    )


@router.post('/analyze-resume', response_model=AnalysisResponse)
async def analyze_resume(
    request: Request,
    file: UploadFile = File(..., description='Resume as PDF or DOCX'),
    job_description: str = Form(..., description='Job description text'),
    user_id: Optional[str] = Depends(get_optional_user),
):
    jd_text = job_description.strip()
    if len(jd_text) < MIN_JD_CHARS:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
                            f'Job description is too short (min {MIN_JD_CHARS} characters).')
    if len(jd_text) > MAX_JD_CHARS:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
                            f'Job description is too long (max {MAX_JD_CHARS} characters).')

    # Read one byte past the limit so oversized uploads are rejected without buffering them fully.
    file_data = await file.read(MAX_FILE_SIZE_BYTES + 1)
    if len(file_data) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                            f'File exceeds the maximum size of {MAX_FILE_SIZE_MB} MB.')

    try:
        # Parsing + embedding + LLM calls are blocking/CPU-bound: run off the event loop.
        result = await run_in_threadpool(
            _run_analysis, request.app.state.scorer, file_data, file.filename or 'resume', jd_text
        )
    except ATSBaseError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, exc.user_message)
    except Exception as exc:
        log_error(exc, context='analyze_resume')
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR,
                            'Something went wrong while analyzing your resume. Please try again.')

    if user_id:
        result['id'] = await supabase_db.save_analysis(user_id, result['filename'], result)
    return result


@router.get('/history', response_model=list[HistoryItem])
async def history(user_id: str = Depends(get_current_user)):
    return await supabase_db.get_user_history(user_id)


@router.delete('/history/{analysis_id}', status_code=status.HTTP_204_NO_CONTENT)
async def delete_history(analysis_id: str, user_id: str = Depends(get_current_user)):
    if not await supabase_db.delete_analysis(analysis_id, user_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, 'Analysis not found')
