# Backend image for Hugging Face Spaces (Docker SDK). Also runs anywhere else:
#   docker build -t ats-backend .
#   docker run -p 7860:7860 --env-file .env ats-backend
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# HF Spaces runs containers as uid 1000; create that user up front so the model
# cache it writes is owned by the runtime user.
RUN useradd -m -u 1000 user
WORKDIR /app

# Dependencies first so code edits don't invalidate this (slow) layer.
# CPU-only torch is ~200 MB vs ~2.5 GB for the default CUDA build.
COPY requirements.txt .
RUN pip install torch --index-url https://download.pytorch.org/whl/cpu \
 && pip install -r requirements.txt \
 && python -m spacy download en_core_web_sm

USER user
ENV HOME=/home/user \
    HF_HOME=/home/user/.cache/huggingface

# Bake the MiniLM weights into the image: no download on cold start, and the
# Space keeps working even if the HF Hub is slow.
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"

COPY --chown=user backend ./backend

# HF Spaces routes traffic to 7860. One worker: each worker holds its own copy of
# the models, and the free tier has limited RAM.
EXPOSE 7860
CMD ["sh", "-c", "uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-7860} --workers 1"]
