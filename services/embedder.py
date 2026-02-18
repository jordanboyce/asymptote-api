"""Embedding service using sentence-transformers."""

from typing import List
import logging
import os
import sys
import numpy as np
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Generates embeddings using sentence-transformers models."""

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        """
        Initialize the embedding service.

        Args:
            model_name: Name of the sentence-transformers model to use
        """
        self.model_name = model_name
        logger.info(f"Loading embedding model: {model_name}")

        # Try to load the model, with helpful error messages for SSL issues
        try:
            self.model = SentenceTransformer(model_name)
        except Exception as e:
            error_msg = str(e).lower()
            if 'ssl' in error_msg or 'certificate' in error_msg:
                logger.error(
                    f"SSL certificate error when downloading model '{model_name}'. "
                    f"This often happens with packaged executables. "
                    f"Try: 1) Run from source instead of exe, or "
                    f"2) Pre-download the model by running: "
                    f"python -c \"from sentence_transformers import SentenceTransformer; SentenceTransformer('{model_name}')\""
                )
            raise

        self.embedding_dim = self.model.get_sentence_embedding_dimension()
        logger.info(f"Model loaded. Embedding dimension: {self.embedding_dim}")

    def embed_texts(self, texts: List[str]) -> np.ndarray:
        """
        Generate embeddings for a list of texts.

        Args:
            texts: List of text strings to embed

        Returns:
            NumPy array of shape (len(texts), embedding_dim)
        """
        if not texts:
            return np.array([]).reshape(0, self.embedding_dim)

        logger.debug(f"Generating embeddings for {len(texts)} texts")
        embeddings = self.model.encode(
            texts,
            show_progress_bar=False,
            convert_to_numpy=True,
        )

        return embeddings

    def embed_query(self, query: str) -> np.ndarray:
        """
        Generate embedding for a single query.

        Args:
            query: Query text

        Returns:
            NumPy array of shape (embedding_dim,)
        """
        logger.debug(f"Generating embedding for query: {query[:50]}...")
        embedding = self.model.encode(
            query,
            show_progress_bar=False,
            convert_to_numpy=True,
        )

        return embedding
