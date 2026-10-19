import pytest

from backend.services.resume_parser import validate_file
from tests.conftest import JD, RESUME


def test_extract_skills_handles_aliases_and_symbols(scorer):
    skills = scorer.extract_skills('Worked with ReactJS, k8s, C++ and Node.js; also Postgres.')
    assert {'React', 'Kubernetes', 'C++', 'Node.js', 'PostgreSQL'} <= skills


def test_ambiguous_aliases_not_matched_in_prose(scorer):
    # "go", "ml", "ts" are common words/fragments and must not count as skills in free text
    assert scorer.extract_skills('I will go to the ML team meeting') == set()


def test_keywords_local_fallback(scorer):
    kw = scorer.score_keywords(RESUME, JD, None, None)
    assert {'Python', 'FastAPI', 'PostgreSQL', 'Docker'} <= set(kw['matched_keywords'])
    assert {'Kubernetes', 'AWS'} <= set(kw['missing_keywords'])
    assert 0 < kw['score'] < 1


def test_keywords_local_fallback_detects_preferred_lines(scorer):
    kw = scorer.score_keywords(RESUME, JD + '\nNice to have: Kafka, GraphQL', None, None)
    assert {'Kafka', 'GraphQL'} == set(kw['missing_preferred'])
    assert 'Kafka' not in kw['missing_keywords']


def test_keywords_with_llm_parse_weights_required_double(scorer):
    jd_parsed = {'required_skills': ['Python', 'Kubernetes'], 'preferred_skills': ['Docker']}
    kw = scorer.score_keywords(RESUME, JD, None, jd_parsed)
    # matched: Python (req, 2) + Docker (pref, 1) out of 2+2+1 = 5
    assert kw['score'] == pytest.approx(3 / 5)
    assert kw['missing_keywords'] == ['Kubernetes']


def test_formatting_detects_contact_and_sections(scorer):
    fmt = scorer.score_formatting(RESUME)
    assert fmt['contact'] == {'email': True, 'phone': True, 'linkedin': False, 'github': True}
    assert set(fmt['sections_found']) == {'experience', 'education', 'skills', 'projects'}


def test_content_counts_verbs_numbers_and_weak_phrases(scorer):
    c = scorer.score_content(RESUME)
    assert c['quantified_bullets'] >= 3
    assert 'responsible for' in c['weak_phrases']


def test_analyze_end_to_end(scorer):
    result = scorer.analyze(RESUME, JD)
    assert 0 <= result['ats_score'] <= 100
    assert sum(c['weight'] for c in result['breakdown'].values()) == pytest.approx(100)
    assert result['suggestions'][0]['priority'] == 'high'


def test_weight_redistributed_when_jd_has_no_skills(scorer):
    result = scorer.analyze(RESUME, 'We want a friendly person who enjoys working with customers every day.')
    assert 'keywords' not in result['breakdown']
    # displayed weights are rounded to 1 decimal, so allow rounding drift
    assert sum(c['weight'] for c in result['breakdown'].values()) == pytest.approx(100, abs=0.5)


@pytest.mark.parametrize('text,expected', [
    ('+91 98765 43210', True),
    ('(555) 123-4567', True),
    ('555.123.4567', True),
    ('B.Tech 2021 - 2025', False),     # years must not look like a phone number
])
def test_phone_detection(text, expected):
    from backend.services.scorer import _has_phone
    assert _has_phone(text) is expected


@pytest.mark.parametrize('data,name,ok', [
    (b'%PDF-1.7 ...', 'cv.pdf', True),
    (b'PK\x03\x04...', 'cv.docx', True),
    (b'not a pdf', 'cv.pdf', False),      # renamed file
    (b'%PDF', 'cv.doc', False),           # legacy doc
    (b'', 'cv.pdf', False),               # empty
    (b'hello', 'cv.txt', False),          # unsupported
])
def test_validate_file(data, name, ok):
    is_valid, msg, _ = validate_file(data, name)
    assert is_valid is ok
    assert ok or msg
