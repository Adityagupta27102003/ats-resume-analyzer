"""HTTP-level tests. TestClient is used *without* a `with` block, so the lifespan
(which loads the real ~90 MB models) never runs; a lightweight scorer is injected
into app.state instead. Responses still pass through FastAPI's response_model
validation, so these tests also catch scorer-output / schema drift."""
import pytest
from fastapi.testclient import TestClient

from backend.api import routes
from backend.core.auth import get_current_user
from backend.database import supabase_db
from backend.main import app
from backend.services import groq_parser
from tests.conftest import JD, RESUME, make_docx, make_pdf

DOCX_MIME = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'


@pytest.fixture
def client(scorer, monkeypatch):
    monkeypatch.setattr(groq_parser, 'is_available', lambda: False)   # never hit the real LLM
    app.state.scorer = scorer
    yield TestClient(app)
    app.dependency_overrides.clear()


def post_resume(client, data=None, name='cv.pdf', jd=JD, mime='application/pdf'):
    data = make_pdf(RESUME) if data is None else data
    return client.post('/api/v1/analyze-resume',
                       files={'file': (name, data, mime)}, data={'job_description': jd})


def test_health(client):
    body = client.get('/api/v1/health').json()
    assert body['status'] == 'ok' and body['models_loaded'] is True
    assert body['groq_enabled'] is False


def test_analyze_pdf_local_parser(client):
    resp = post_resume(client)
    assert resp.status_code == 200
    body = resp.json()
    assert body['parser'] == 'local'
    assert body['job_title'] == 'Backend Engineer'       # first short JD line
    assert body['filename'] == 'cv.pdf'
    assert 0 <= body['ats_score'] <= 100
    assert 'Kubernetes' in body['missing_keywords']
    assert body['id'] is None                             # anonymous → not saved


def test_analyze_docx(client):
    resp = post_resume(client, make_docx(RESUME), 'cv.docx', mime=DOCX_MIME)
    assert resp.status_code == 200
    assert 'Python' in resp.json()['matched_keywords']


def test_groq_failure_falls_back_to_local(client, monkeypatch):
    def boom(_):
        raise RuntimeError('groq down')
    monkeypatch.setattr(groq_parser, 'is_available', lambda: True)
    monkeypatch.setattr(groq_parser, 'parse_resume', boom)
    monkeypatch.setattr(groq_parser, 'parse_job_description', boom)

    resp = post_resume(client)
    assert resp.status_code == 200
    assert resp.json()['parser'] == 'local'


def test_groq_parse_is_used_when_available(client, monkeypatch):
    monkeypatch.setattr(groq_parser, 'is_available', lambda: True)
    monkeypatch.setattr(groq_parser, 'parse_resume', lambda t: {'name': 'Aditya Sharma', 'skills': ['Python']})
    monkeypatch.setattr(groq_parser, 'parse_job_description', lambda t: {
        'job_title': 'Senior Backend Engineer', 'required_skills': ['Python', 'Kubernetes'],
        'preferred_skills': [], 'key_responsibilities': ['Build scalable APIs in Python'],
    })

    body = post_resume(client).json()
    assert body['parser'] == 'groq'
    assert body['job_title'] == 'Senior Backend Engineer'
    assert body['candidate_name'] == 'Aditya Sharma'
    assert body['missing_keywords'] == ['Kubernetes']


@pytest.mark.parametrize('jd', ['too short', 'x' * 20001])
def test_job_description_length_validated(client, jd):
    assert post_resume(client, jd=jd).status_code == 422


def test_oversized_file_rejected(client):
    resp = post_resume(client, b'%PDF' + b'0' * (5 * 1024 * 1024))
    assert resp.status_code == 413


@pytest.mark.parametrize('data,name,msg', [
    (b'hello', 'cv.txt', 'Unsupported file type'),
    (b'%PDF-1.4 junk', 'cv.pdf', 'Failed to extract text'),
    (b'', 'cv.pdf', 'empty'),
])
def test_bad_files_return_readable_422(client, data, name, msg):
    resp = post_resume(client, data, name)
    assert resp.status_code == 422
    assert msg in resp.json()['detail']


def test_unexpected_error_returns_generic_500(client, monkeypatch):
    def crash(*args):
        raise RuntimeError('internal detail that must not leak')
    monkeypatch.setattr(routes, '_run_analysis', crash)

    resp = post_resume(client)
    assert resp.status_code == 500
    assert 'internal detail' not in resp.json()['detail']


def test_history_requires_login(client):
    assert client.get('/api/v1/history').status_code == 401


def test_history_returns_user_rows(client, monkeypatch):
    app.dependency_overrides[get_current_user] = lambda: 'user-1'

    async def fake_history(user_id):
        assert user_id == 'user-1'
        return [{'id': 'a1', 'filename': 'cv.pdf', 'job_title': 'SDE', 'ats_score': 72,
                 'keyword_match': 60.0, 'created_at': '2026-10-19T10:00:00Z', 'analysis_result': {}}]
    monkeypatch.setattr(supabase_db, 'get_user_history', fake_history)

    rows = client.get('/api/v1/history').json()
    assert [r['id'] for r in rows] == ['a1']


def test_delete_unknown_history_returns_404(client, monkeypatch):
    app.dependency_overrides[get_current_user] = lambda: 'user-1'

    async def not_found(analysis_id, user_id):
        return False
    monkeypatch.setattr(supabase_db, 'delete_analysis', not_found)

    assert client.delete('/api/v1/history/does-not-exist').status_code == 404
