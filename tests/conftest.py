"""Shared fixtures. Tests never load the real spaCy/MiniLM models: a blank spaCy
tokenizer + a bag-of-words FakeEmbedder keep the suite fast (~seconds) and
deterministic, while exercising the exact same scoring code paths."""
import io

import numpy as np
import pytest
import spacy
from docx import Document

from backend.services.scorer import ATSScorer

RESUME = """Aditya Sharma
aditya@example.com | +91 98765 43210 | github.com/aditya

Skills
Python, FastAPI, React, PostgreSQL, Docker, Git, REST APIs

Experience
Software Engineer Intern, Acme Corp
Built a FastAPI service handling 10k requests per day with PostgreSQL
Reduced API latency by 40% by adding Redis caching
Responsible for writing unit tests

Projects
Developed a React dashboard to visualize sales data for 200 users

Education
B.Tech Computer Science, XYZ University, 2025
"""

JD = """Backend Engineer
We are looking for a backend engineer to build scalable APIs.
Required: Python, FastAPI, PostgreSQL, Docker, Kubernetes, AWS
Design and build RESTful services that handle high traffic workloads
Experience with caching and performance optimization of backend systems
"""


class FakeEmbedder:
    """Deterministic bag-of-words embedder — stands in for MiniLM in unit tests."""
    def encode(self, texts, normalize_embeddings=True, batch_size=32):
        vecs = np.zeros((len(texts), 256))
        for i, t in enumerate(texts):
            for w in t.lower().split():
                vecs[i, hash(w) % 256] += 1
        return vecs / np.maximum(np.linalg.norm(vecs, axis=1, keepdims=True), 1e-9)


@pytest.fixture(scope='session')
def scorer():
    return ATSScorer(spacy.blank('en'), FakeEmbedder())


def make_docx(text: str) -> bytes:
    doc = Document()
    for line in text.splitlines():
        doc.add_paragraph(line)
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


def make_pdf(text: str) -> bytes:
    """Minimal single-page PDF with real, selectable text (no PDF library needed).
    Byte offsets for the xref table are computed as objects are written."""
    def esc(s: str) -> str:
        return s.replace('\\', '\\\\').replace('(', '\\(').replace(')', '\\)')

    lines = ' '.join(f'({esc(ln)}) Tj T*' for ln in text.splitlines())
    stream = f'BT /F1 10 Tf 14 TL 50 780 Td {lines} ET'.encode('latin-1')
    objects = [
        b'<< /Type /Catalog /Pages 2 0 R >>',
        b'<< /Type /Pages /Kids [3 0 R] /Count 1 >>',
        b'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 842] '
        b'/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>',
        b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>',
        b'<< /Length %d >>\nstream\n' % len(stream) + stream + b'\nendstream',
    ]
    out = bytearray(b'%PDF-1.4\n')
    offsets = []
    for i, body in enumerate(objects, start=1):
        offsets.append(len(out))
        out += b'%d 0 obj\n' % i + body + b'\nendobj\n'
    xref_at = len(out)
    out += b'xref\n0 %d\n0000000000 65535 f \n' % (len(objects) + 1)
    out += b''.join(b'%010d 00000 n \n' % off for off in offsets)
    out += b'trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n' % (len(objects) + 1, xref_at)
    return bytes(out)
