"""FAISS-based vector store with SQLite metadata for scalability."""

from pathlib import Path
from typing import List, Optional
import logging
import numpy as np
import faiss

from models.schemas import ChunkMetadata, SearchResult
from services.metadata_store import MetadataStore

logger = logging.getLogger(__name__)


class VectorStore:
    """
    FAISS-based vector store with SQLite metadata storage.

    Uses SQLite for metadata, providing:
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
        self.embeddings_path = self.index_dir / "embeddings.npy"

        # FAISS index
        self.index: Optional[faiss.Index] = None

        # Embeddings storage: NumPy array of embeddings
        self.embeddings: Optional[np.ndarray] = None

        # SQLite metadata store
        self.metadata_store = MetadataStore(self.metadata_db_path)

        self._load_or_create_index()

    def _load_or_create_index(self):
        """Load existing index from disk or create a new one."""
        if self.index_path.exists():
            logger.info("Loading existing FAISS index")
            self.index = faiss.read_index(str(self.index_path))

            # Load embeddings if they exist
            if self.embeddings_path.exists():
                self.embeddings = np.load(str(self.embeddings_path))
                logger.info(f"Loaded embeddings array with shape {self.embeddings.shape}")
            else:
                logger.warning("Embeddings file not found - deletion will not work properly")
                self.embeddings = None

            total_chunks = self.metadata_store.get_total_chunks()
            logger.info(f"Loaded index with {total_chunks} chunks")
        else:
            logger.info("Creating new FAISS index")
            # Use IndexFlatIP for cosine similarity (inner product)
            # Vectors must be L2 normalized before adding
            self.index = faiss.IndexFlatIP(self.embedding_dim)
            self.embeddings = None
            logger.info("Created new index")

    def load(self):
        """Reload the index from disk (public method for external reload)."""
        logger.info("Reloading index from disk...")
        self._load_or_create_index()

    def close(self):
        """Close the vector store and release resources."""
        logger.info("Closing vector store...")
        # Clear references to allow garbage collection
        self.index = None
        self.embeddings = None
        self.metadata_store = None

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

        # Store embeddings
        if self.embeddings is None:
            self.embeddings = embeddings_normalized.astype(np.float32)
        else:
            self.embeddings = np.vstack([self.embeddings, embeddings_normalized.astype(np.float32)])

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
                # v3.0: Format-aware metadata
                source_format=chunk.get("source_format"),
                extraction_method=chunk.get("extraction_method"),
                csv_row_number=chunk.get("csv_row_number"),
                csv_columns=chunk.get("csv_columns"),
                csv_values=chunk.get("csv_values"),
            )
            results.append(result)

        return results

    def delete_document(self, document_id: str) -> int:
        """
        Delete all chunks belonging to a document.

        Note: FAISS doesn't support efficient deletion, so we rebuild the index.

        Args:
            document_id: Document ID to delete

        Returns:
            Number of chunks deleted
        """
        # Get indices to delete from metadata store
        indices_to_delete = set(self.metadata_store.get_document_chunk_indices(document_id))

        if len(indices_to_delete) == 0:
            logger.warning(f"Document {document_id} not found in index")
            return 0

        num_deleted = len(indices_to_delete)
        logger.info(f"Deleting {num_deleted} chunks for document {document_id}")

        # Delete from metadata (SQLite)
        self.metadata_store.delete_document(document_id)

        # Rebuild FAISS index with remaining embeddings
        if self.embeddings is not None:
            new_embeddings = []
            for idx in range(len(self.embeddings)):
                if idx not in indices_to_delete:
                    new_embeddings.append(self.embeddings[idx])

            # Rebuild FAISS index
            logger.info(f"Rebuilding index with {len(new_embeddings)} remaining chunks")
            self.index = faiss.IndexFlatIP(self.embedding_dim)

            if len(new_embeddings) > 0:
                self.embeddings = np.array(new_embeddings, dtype=np.float32)
                self.index.add(self.embeddings)
                logger.info(f"Re-added {len(new_embeddings)} vectors to index")
            else:
                self.embeddings = None
                logger.info("Index is now empty")
        else:
            logger.warning("No embeddings stored - cannot rebuild index properly")

        logger.info(f"Successfully deleted document {document_id}")

        return num_deleted

    def list_documents(self) -> List[dict]:
        """
        List all indexed documents with their metadata.

        Returns:
            List of document metadata dictionaries
        """
        return self.metadata_store.list_documents()

    def save(self):
        """Persist the FAISS index, embeddings, and metadata to disk."""
        logger.info(f"Saving FAISS index with {self.index.ntotal} vectors")
        faiss.write_index(self.index, str(self.index_path))

        # Save embeddings
        if self.embeddings is not None:
            np.save(str(self.embeddings_path), self.embeddings)
            logger.info(f"Saved embeddings array with shape {self.embeddings.shape}")

        # Metadata is already persisted in SQLite
        logger.info("Index saved successfully")

    def get_total_chunks(self) -> int:
        """Get the total number of chunks in the index."""
        return self.metadata_store.get_total_chunks()

    def clear_index(self):
        """Clear all data from the index and metadata store."""
        logger.info("Clearing vector store index and metadata")

        # Create new empty FAISS index
        self.index = faiss.IndexFlatIP(self.embedding_dim)
        self.embeddings = None

        # Clear all metadata from database
        self.metadata_store.clear_all()

        # Save the empty index
        self.save()

        logger.info("Vector store cleared successfully")

