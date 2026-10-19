# Backend image. Deployed on Render (see render.yaml); runs anywhere Docker does:
#   docker build -t ats-backend .
#   docker run -p 8000:8000 -e PORT=8000 --env-file .env ats-backend
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    EMBEDDING_CACHE_DIR=/app/models

RUN useradd -m -u 1000 user
WORKDIR /app

# Dependencies first so code edits don't invalidate this layer. No PyTorch: embeddings
# run on ONNX Runtime, which keeps the image small and RAM under the 512 MB free tier.
COPY requirements.txt .
RUN pip install -r requirements.txt

# Bake the MiniLM ONNX weights into the image: no download on cold start.
RUN python -c "from fastembed import TextEmbedding; TextEmbedding('sentence-transformers/all-MiniLM-L6-v2', cache_dir='/app/models')" \
 && chown -R user /app/models

COPY --chown=user backend ./backend
USER user

# Render injects $PORT. One worker: each worker would hold its own copy of the model.
EXPOSE 8000
CMD ["sh", "-c", "uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1"]
