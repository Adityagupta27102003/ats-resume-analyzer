"""Sentence embeddings with all-MiniLM-L6-v2 (a 6-layer distilled BERT) on ONNX Runtime.

Same model and same vectors as sentence-transformers (cosine 1.0 between the two),
but without PyTorch: ~150 MB of RAM instead of ~1 GB and a much smaller image, which
is what lets the API run on a 512 MB free-tier instance.
"""
import numpy as np
from fastembed import TextEmbedding


class OnnxEmbedder:
    """Exposes the subset of SentenceTransformer.encode() the scorer uses, so the
    scorer (and the FakeEmbedder in tests) don't depend on which runtime is behind it."""

    def __init__(self, model_name: str, cache_dir: str | None = None):
        self.model = TextEmbedding(model_name, cache_dir=cache_dir)

    def encode(self, texts: list[str], normalize_embeddings: bool = True, batch_size: int = 32) -> np.ndarray:
        emb = np.array(list(self.model.embed(texts, batch_size=batch_size)), dtype=np.float32)
        if normalize_embeddings:
            emb /= np.maximum(np.linalg.norm(emb, axis=1, keepdims=True), 1e-12)
        return emb
