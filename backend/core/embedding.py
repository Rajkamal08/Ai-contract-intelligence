"""
Embedding Module
────────────────
Generates dense vector embeddings from text using SentenceTransformers.
Uses singleton pattern to avoid reloading the model on every request.
"""

import numpy as np
from sentence_transformers import SentenceTransformer
from loguru import logger
from config import settings


class EmbeddingEngine:
    """
    Singleton embedding engine using SentenceTransformers.

    The model is loaded once and reused across all requests.
    Model: all-MiniLM-L6-v2 (384-dimensional embeddings, fast + accurate)
    """

    _instance = None
    _model: SentenceTransformer | None = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if self._model is None:
            self._load_model()

    def _load_model(self):
        """Load the SentenceTransformer model."""
        model_name = settings.embedding_model_name
        logger.info(f"Loading embedding model: {model_name}")

        try:
            self._model = SentenceTransformer(model_name)
            # Get embedding dimension
            test_embedding = self._model.encode("test")
            self._dimension = len(test_embedding)
            logger.info(
                f"Model loaded successfully. Dimension: {self._dimension}"
            )
        except Exception as e:
            logger.error(f"Failed to load embedding model: {e}")
            raise RuntimeError(f"Embedding model loading failed: {e}")

    @property
    def dimension(self) -> int:
        """Return the embedding dimension."""
        return self._dimension

    def embed_text(self, text: str) -> list[float]:
        """
        Generate embedding for a single text string.

        Args:
            text: Input text to embed.

        Returns:
            List of floats representing the embedding vector.
        """
        if not text or not text.strip():
            raise ValueError("Cannot embed empty text")

        embedding = self._model.encode(text, normalize_embeddings=True)
        return embedding.tolist()

    def embed_batch(self, texts: list[str], batch_size: int = 32) -> list[list[float]]:
        """
        Generate embeddings for a batch of texts.

        Args:
            texts: List of input texts.
            batch_size: Number of texts to process at once.

        Returns:
            List of embedding vectors.
        """
        if not texts:
            return []

        # Filter out empty texts but track indices
        valid_texts = []
        valid_indices = []

        for i, text in enumerate(texts):
            if text and text.strip():
                valid_texts.append(text)
                valid_indices.append(i)

        if not valid_texts:
            return [[] for _ in texts]

        logger.info(f"Embedding {len(valid_texts)} texts (batch_size={batch_size})")

        embeddings = self._model.encode(
            valid_texts,
            batch_size=batch_size,
            normalize_embeddings=True,
            show_progress_bar=len(valid_texts) > 100,
        )

        # Reconstruct full list with empty embeddings for filtered texts
        result = [[] for _ in texts]
        for idx, emb in zip(valid_indices, embeddings):
            result[idx] = emb.tolist()

        logger.info(f"Embedding complete. Shape: ({len(valid_texts)}, {self._dimension})")
        return result

    def embed_query(self, query: str) -> list[float]:
        """
        Generate embedding for a search query.
        Alias for embed_text — kept separate for future query-specific
        optimizations (e.g., query prefixing for asymmetric models).
        """
        return self.embed_text(query)
