"""ATS scoring engine.

Final score (0-100) is a weighted sum of four components, each scored 0..1:

  keywords   — what fraction of the JD's hard skills appear in the resume
               (required skills count double, aliases + fuzzy matching via rapidfuzz)
  semantic   — for each JD requirement, cosine similarity (MiniLM / BERT embeddings)
               to the closest resume line, averaged and rescaled
  content    — action-verb bullets, quantified impact, absence of weak phrases
  formatting — contact info, standard section headings, sensible length

Groq-parsed structure is used when available; everything has a local fallback so
the pipeline still works (slightly less precisely) without an LLM.
"""
import re
from typing import Optional

import numpy as np
from rapidfuzz import fuzz
from spacy.matcher import PhraseMatcher

from backend.core.config import SCORE_WEIGHTS, SEMANTIC_SIM_FLOOR, SEMANTIC_SIM_CEIL
from backend.services.skills import (
    SKILLS, AMBIGUOUS_ALIASES, ACTION_VERBS, WEAK_PHRASES, canonicalize,
)

EMAIL_RE = re.compile(r'[\w.+-]+@[\w-]+\.[\w.-]+')
# Any run of digits/separators; validated by digit count (10-13) in _has_phone, which
# covers "+91 98765 43210", "(555) 123-4567", "555.123.4567" without per-country regexes.
PHONE_CANDIDATE_RE = re.compile(r'\+?\(?\d[\d\s().-]{8,18}\d')
NUMBER_RE = re.compile(r'(\d+(\.\d+)?\s?(%|x|k|m|\+)|\$\s?\d|\b\d{2,}\b)', re.IGNORECASE)
BULLET_PREFIX_RE = re.compile(r'^[\s•●▪◦\-*–>]+')
PREFERRED_LINE_RE = re.compile(r'nice[\s-]to[\s-]have|preferred|bonus|good to have|is a plus|\bplus\b', re.IGNORECASE)

SECTION_PATTERNS = {
    'experience': r'(work |professional )?experience|employment( history)?|internships?',
    'education':  r'education|academics?|academic background',
    'skills':     r'(technical |core )?skills|technologies|tech stack|competencies',
    'projects':   r'(personal |academic |key )?projects',
}

IDEAL_WORDS = (350, 1100)
MAX_CHUNKS = 120
MAX_REQUIREMENTS = 30


def _clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))


def _has_phone(text: str) -> bool:
    return any(10 <= sum(ch.isdigit() for ch in m) <= 13 for m in PHONE_CANDIDATE_RE.findall(text))


def _lines(text: str) -> list[str]:
    return [BULLET_PREFIX_RE.sub('', ln).strip() for ln in text.splitlines() if ln.strip()]


class ATSScorer:
    def __init__(self, nlp, embedder):
        self.nlp = nlp
        self.embedder = embedder
        self.matcher = PhraseMatcher(nlp.vocab, attr='LOWER')
        for canonical, aliases in SKILLS.items():
            terms = [t for t in [canonical, *aliases] if t.lower() not in AMBIGUOUS_ALIASES]
            if terms:
                self.matcher.add(canonical, [nlp.make_doc(t) for t in terms])

    # ── skill extraction ───────────────────────────────────────────────

    def extract_skills(self, text: str) -> set[str]:
        doc = self.nlp.make_doc(text)   # tokenizer only — no need for the full pipeline
        return {self.nlp.vocab.strings[match_id] for match_id, _, _ in self.matcher(doc)}

    def _has_skill(self, skill: str, resume_lower: str, resume_skills_lower: set[str]) -> bool:
        s = skill.lower()
        if s in resume_skills_lower:
            return True
        # whole-word containment (re.escape handles C++, .NET, CI/CD)
        if re.search(rf'(?<![\w+#]){re.escape(s)}(?![\w+#])', resume_lower):
            return True
        # fuzzy match against the resume's skill list ("REST APIs" vs "RESTful API")
        return any(fuzz.token_set_ratio(s, r) >= 88 for r in resume_skills_lower if len(r) > 3)

    # ── components ─────────────────────────────────────────────────────

    def score_keywords(self, resume_text: str, jd_text: str,
                       resume_parsed: Optional[dict], jd_parsed: Optional[dict]) -> Optional[dict]:
        resume_skills = self.extract_skills(resume_text)
        if resume_parsed:
            resume_skills |= {canonicalize(s) for s in resume_parsed.get('skills', []) if isinstance(s, str)}
        resume_skills_lower = {s.lower() for s in resume_skills}
        resume_lower = resume_text.lower()

        if jd_parsed and (jd_parsed.get('required_skills') or jd_parsed.get('preferred_skills')):
            required = {canonicalize(s) for s in jd_parsed['required_skills'] if isinstance(s, str) and s.strip()}
            preferred = {canonicalize(s) for s in jd_parsed['preferred_skills'] if isinstance(s, str) and s.strip()} - required
        else:
            # Local fallback: skills on "nice to have / preferred / bonus" lines are preferred.
            pref_text = '\n'.join(ln for ln in jd_text.splitlines() if PREFERRED_LINE_RE.search(ln))
            preferred = self.extract_skills(pref_text)
            required = self.extract_skills(jd_text) - preferred

        if not required and not preferred:
            return None   # JD has no recognisable hard skills — component is skipped

        matched_req = sorted(s for s in required if self._has_skill(s, resume_lower, resume_skills_lower))
        matched_pref = sorted(s for s in preferred if self._has_skill(s, resume_lower, resume_skills_lower))
        missing_req = sorted(required - set(matched_req))
        missing_pref = sorted(preferred - set(matched_pref))

        total = 2 * len(required) + len(preferred)
        score = (2 * len(matched_req) + len(matched_pref)) / total
        return {
            'score': score,
            'matched_keywords': matched_req + matched_pref,
            'missing_keywords': missing_req,
            'missing_preferred': missing_pref,
            'resume_skills': sorted(resume_skills),
        }

    def _resume_chunks(self, resume_text: str) -> list[str]:
        # Each bullet/line is a unit of evidence; very short lines (headers, dates)
        # are merged into the next one so they don't produce noisy embeddings.
        chunks, buf = [], ''
        for ln in _lines(resume_text):
            buf = f'{buf} {ln}'.strip()
            if len(buf.split()) >= 5:
                chunks.append(buf)
                buf = ''
        if buf:
            chunks.append(buf)
        return chunks[:MAX_CHUNKS]

    def _jd_requirements(self, jd_text: str, jd_parsed: Optional[dict]) -> list[str]:
        if jd_parsed and jd_parsed.get('key_responsibilities'):
            reqs = [r for r in jd_parsed['key_responsibilities'] if isinstance(r, str) and r.strip()]
        else:
            reqs = [ln for ln in _lines(jd_text) if len(ln.split()) >= 5]
        return reqs[:MAX_REQUIREMENTS] or [jd_text[:1000]]

    def score_semantic(self, resume_text: str, jd_text: str, jd_parsed: Optional[dict]) -> dict:
        chunks = self._resume_chunks(resume_text)
        reqs = self._jd_requirements(jd_text, jd_parsed)

        # normalize_embeddings=True → unit vectors, so dot product == cosine similarity
        emb = self.embedder.encode(reqs + chunks, normalize_embeddings=True, batch_size=32)
        req_emb, chunk_emb = emb[:len(reqs)], emb[len(reqs):]
        sim = req_emb @ chunk_emb.T                  # (n_reqs, n_chunks)
        best_idx = sim.argmax(axis=1)
        best_sim = sim.max(axis=1)

        rescaled = np.clip((best_sim - SEMANTIC_SIM_FLOOR) / (SEMANTIC_SIM_CEIL - SEMANTIC_SIM_FLOOR), 0, 1)
        requirements = [
            {
                'requirement': reqs[i],
                'best_match': chunks[best_idx[i]],
                'similarity': round(float(rescaled[i]) * 100, 1),
            }
            for i in range(len(reqs))
        ]
        requirements.sort(key=lambda r: r['similarity'])
        return {
            'score': float(rescaled.mean()),
            'raw_cosine_mean': round(float(best_sim.mean()), 4),
            'requirements': requirements,     # weakest first — these are the gaps
        }

    def score_content(self, resume_text: str) -> dict:
        lines = [ln for ln in _lines(resume_text) if len(ln.split()) >= 6]   # bullet-like lines
        if not lines:
            return {'score': 0.0, 'bullet_count': 0, 'action_verb_ratio': 0.0,
                    'quantified_bullets': 0, 'weak_phrases': []}

        verb_lines = sum(1 for ln in lines if ln.split()[0].lower().strip(',.:;') in ACTION_VERBS)
        quantified = sum(1 for ln in lines if NUMBER_RE.search(ln))
        lower = resume_text.lower()
        weak = [p for p in WEAK_PHRASES if p in lower]

        verb_ratio = verb_lines / len(lines)
        verb_score = _clamp01(verb_ratio / 0.6)          # 60%+ of bullets start with a strong verb → full marks
        quant_score = _clamp01(quantified / 5)           # 5+ quantified bullets → full marks
        weak_score = _clamp01(1 - 0.25 * len(weak))
        return {
            'score': 0.4 * verb_score + 0.4 * quant_score + 0.2 * weak_score,
            'bullet_count': len(lines),
            'action_verb_ratio': round(verb_ratio * 100, 1),
            'quantified_bullets': quantified,
            'weak_phrases': weak,
        }

    def score_formatting(self, resume_text: str) -> dict:
        lower = resume_text.lower()
        contact = {
            'email': bool(EMAIL_RE.search(resume_text)),
            'phone': _has_phone(resume_text),
            'linkedin': 'linkedin.com' in lower,
            'github': 'github.com' in lower,
        }
        # A heading is a short line that is (almost) only the section name.
        headers = [ln.lower().strip(':') for ln in _lines(resume_text) if len(ln.split()) <= 4]
        found = [name for name, pat in SECTION_PATTERNS.items()
                 if any(re.fullmatch(pat, h) for h in headers)]
        missing = [name for name in SECTION_PATTERNS if name not in found]
        words = len(resume_text.split())

        lo, hi = IDEAL_WORDS
        if lo <= words <= hi:
            length_score = 1.0
        elif words < lo:
            length_score = words / lo
        else:
            length_score = _clamp01(1 - (words - hi) / hi)

        contact_score = (contact['email'] + contact['phone']) / 2 * 0.8 + (contact['linkedin'] or contact['github']) * 0.2
        score = 0.35 * contact_score + 0.45 * len(found) / len(SECTION_PATTERNS) + 0.2 * length_score
        return {
            'score': score,
            'contact': contact,
            'sections_found': found,
            'sections_missing': missing,
            'word_count': words,
        }

    # ── orchestration ──────────────────────────────────────────────────

    def analyze(self, resume_text: str, jd_text: str,
                resume_parsed: Optional[dict] = None, jd_parsed: Optional[dict] = None) -> dict:
        keywords = self.score_keywords(resume_text, jd_text, resume_parsed, jd_parsed)
        semantic = self.score_semantic(resume_text, jd_text, jd_parsed)
        content = self.score_content(resume_text)
        formatting = self.score_formatting(resume_text)

        components = {'keywords': keywords, 'semantic': semantic, 'content': content, 'formatting': formatting}
        # If a component can't be computed, spread its weight over the others proportionally.
        active = {k: w for k, w in SCORE_WEIGHTS.items() if components[k] is not None}
        scale = 100 / sum(active.values())
        breakdown = {
            k: {'score': round(components[k]['score'] * 100, 1), 'weight': round(w * scale, 1)}
            for k, w in active.items()
        }
        ats_score = round(sum(components[k]['score'] * w * scale for k, w in active.items()))

        return {
            'ats_score': ats_score,
            'score_label': _label(ats_score),
            'breakdown': breakdown,
            'keyword_match': breakdown.get('keywords', {}).get('score', 0.0),
            'matched_keywords': keywords['matched_keywords'] if keywords else [],
            'missing_keywords': keywords['missing_keywords'] if keywords else [],
            'missing_preferred': keywords['missing_preferred'] if keywords else [],
            'resume_skills': keywords['resume_skills'] if keywords else sorted(self.extract_skills(resume_text)),
            'semantic': {k: v for k, v in semantic.items() if k != 'score'},
            'content': {k: v for k, v in content.items() if k != 'score'},
            'formatting': {k: v for k, v in formatting.items() if k != 'score'},
            'suggestions': build_suggestions(keywords, semantic, content, formatting),
        }


def _label(score: int) -> str:
    if score >= 80: return 'Excellent'
    if score >= 65: return 'Good'
    if score >= 50: return 'Fair'
    return 'Needs Work'


def build_suggestions(keywords, semantic, content, formatting) -> list[dict]:
    out = []
    def add(priority, category, message):
        out.append({'priority': priority, 'category': category, 'message': message})

    if keywords and keywords['missing_keywords']:
        top = ', '.join(keywords['missing_keywords'][:8])
        add('high', 'keywords', f'Add these required skills if you have them: {top}. '
                                'ATS filters often reject resumes missing required keywords.')
    if keywords and keywords['missing_preferred']:
        add('low', 'keywords', f'Nice-to-have skills you could mention: {", ".join(keywords["missing_preferred"][:6])}.')

    weak_reqs = [r for r in semantic['requirements'] if r['similarity'] < 40][:3]
    for r in weak_reqs:
        add('medium', 'relevance', f'Nothing in your resume closely addresses: "{r["requirement"][:140]}". '
                                   'Add a bullet showing related experience.')

    if not formatting['contact']['email'] or not formatting['contact']['phone']:
        add('high', 'formatting', 'Include both an email address and phone number at the top of your resume.')
    if formatting['sections_missing']:
        add('medium', 'formatting', f'Add clearly labelled section headings for: {", ".join(formatting["sections_missing"])}. '
                                    'ATS parsers rely on standard headings.')
    if not formatting['contact']['linkedin'] and not formatting['contact']['github']:
        add('low', 'formatting', 'Add a LinkedIn or GitHub profile link.')
    wc = formatting['word_count']
    if wc < IDEAL_WORDS[0]:
        add('medium', 'formatting', f'Your resume is short ({wc} words). Aim for {IDEAL_WORDS[0]}-{IDEAL_WORDS[1]} words.')
    elif wc > IDEAL_WORDS[1]:
        add('medium', 'formatting', f'Your resume is long ({wc} words). Trim to the most relevant content.')

    if content['quantified_bullets'] < 3:
        add('high', 'content', 'Quantify your impact with numbers (e.g. "reduced latency by 40%", "served 10k users").')
    if content['action_verb_ratio'] < 50:
        add('medium', 'content', 'Start more bullets with strong action verbs (Built, Designed, Optimized, Led...).')
    if content['weak_phrases']:
        add('medium', 'content', f'Replace weak phrases like "{content["weak_phrases"][0]}" with concrete accomplishments.')

    order = {'high': 0, 'medium': 1, 'low': 2}
    return sorted(out, key=lambda s: order[s['priority']])
