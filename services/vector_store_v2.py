"""FAISS-based vector store with SQLite metadata for scalability."""

from pathlib import Path
from typing import List, Optional
import logging
import numpy as np
import faiss

from models.schemas import ChunkMetadata, SearchResult
from services.metadata_store import MetadataStore

logger = logging.getLogger(__name__)


class VectorStoreV2:
    """
    FAISS-based vector store with SQLite metadata storage.

    This version uses SQLite instead of JSON for metadata, providing:
    - Constant memory usage regardless of document count
    - Faster lookups with indexed queries
    - Better scalability for large collections
    """

    def __init__(self, index_dir: Path, embedding_dim: int = 384):
        """
        Initialize the vector store.

        Args:
            index_dir: Directory to store FAISS index and metadata
            embedding_dim: Dimension of embedding vectors
        """
        self.index_dir = index_dir
        self.index_dir.mkdir(parents=True, exist_ok=True)
        self.embedding_dim = embedding_dim

        self.index_path = self.index_dir / "faiss.index"
        self.metadata_db_path = self.index_dir / "metadata.db"

        # FAISS index
        self.index: Optional[faiss.Index] = None

        # SQLite metadata store
        self.metadata_store = MetadataStore(self.metadata_db_path)

        self._load_or_create_index()

    def _load_or_create_index(self):
        """Load existing index from disk or create a new one."""
        if self.index_path.exists():
            logger.info("Loading existing FAISS index")
            self.index = faiss.read_index(str(self.index_path))

            total_chunks = self.metadata_store.get_total_chunks()
            logger.info(f"Loaded index with {total_chunks} chunks")
        else:
            logger.info("Creating new FAISS index")
            # Use IndexFlatIP for cosine similarity (inner product)
            # Vectors must be L2 normalized before adding
            self.index = faiss.IndexFlatIP(self.embedding_dim)
            logger.info("Created new index")

    def add_chunks(self, chunks: List[ChunkMetadata], embeddings: np.ndarray):
        """
        Add chunks and their embeddings to the index.

        Args:
            chunks: List of ChunkMetadata objects
            embeddings: NumPy array of shape (len(chunks), embedding_dim)
        """
        if len(chunks) != len(embeddings):
            raise ValueError("Number of chunks must match number of embeddings")

        if len(chunks) == 0:
            return

        # Normalize embeddings for cosine similarity
        embeddings_normalized = embeddings / np.linalg.norm(embeddings, axis=1, keepdims=True)

        # Add to FAISS index
        self.index.add(embeddings_normalized.astype(np.float32))

        # Add metadata to SQLite
        chunk_dicts = [chunk.model_dump() for chunk in chunks]
        self.metadata_store.add_chunks(chunk_dicts)

        logger.info(f"Added {len(chunks)} chunks to index")

    def search(self, query_embedding: np.ndarray, top_k: int = 10) -> List[SearchResult]:
        """
        Search for similar chunks.

        Args:
            query_embedding: Query embedding vector
            top_k: Number of results to return

        Returns:
            List of SearchResult objects, sorted by similarity (highest first)
        """
        if self.index.ntotal == 0:
            logger.warning("Index is empty, returning no results")
            return []

        # Normalize query for cosine similarity
        query_normalized = query_embedding / np.linalg.norm(query_embedding)
        query_normalized = query_normalized.reshape(1, -1).astype(np.float32)

        # Search
        k = min(top_k, self.index.ntotal)
        similarities, indices = self.index.search(query_normalized, k)

        # Convert to SearchResult objects
        results = []
        for similarity, idx in zip(similarities[0], indices[0]):
            if idx == -1:  # FAISS returns -1 for empty results
                continue

            # Fetch metadata from SQLite by index
            chunk = self.metadata_store.get_chunk_by_index(int(idx))
            if not chunk:
                logger.warning(f"No metadata found for index {idx}")
                continue

            result = SearchResult(
                filename=chunk["filename"],
                page_number=chunk["page_number"],
                text_snippet=chunk["text"],
                similarity_score=float(similarity),
                document_id=chunk["document_id"],
                chunk_id=chunk["chunk_id"],
                pdf_url="",  # Will be populated by the API endpoint
                page_url="",  # Will be populated by the API endpoint
            )
            results.append(result)

        return results

    def delete_document(self, document_id: str) -> int:
        """
        Delete all chunks belonging to a document from metadata.

        Note: FAISS vectors remain in the index (FAISS limitation).
        For full cleanup, rebuild the index after deleting many documents.

        Args:
            document_id: Document ID to delete

        Returns:
            Number of chunks deleted from metadata
        """
        num_deleted = self.metadata_store.delete_document(document_id)

        if num_deleted > 0:
            logger.warning(
                f"Deleted {num_deleted} chunks from metadata. "
                f"FAISS vectors remain (rebuild index for full cleanup)"
            )

        return num_deleted

    def list_documents(self) -> List[dict]:
        """
        List all indexed documents with their metadata.

        Returns:
            List of document metadata dictionaries
        """
        return self.metadata_store.list_documents()

    def save(self):
        """Persist the FAISS index to disk. Metadata is already persisted in SQLite."""
        logger.info(f"Saving FAISS index with {self.index.ntotal} vectors")
        faiss.write_index(self.index, str(self.index_path))
        logger.info("Index saved successfully")

    def get_total_chunks(self) -> int:
        """Get the total number of chunks in the index."""
        return self.metadata_store.get_total_chunks()

    def rebuild_index(self):
        """
        Rebuild FAISS index to remove deleted documents.

        WARNING: This requires re-embedding all documents.
        Not implemented in current version - see SCALING.md for alternatives.
        """
        raise NotImplementedError(
            "Index rebuild requires re-embedding. "
            "Consider migrating to pgvector or Qdrant for better deletion support."
        )
