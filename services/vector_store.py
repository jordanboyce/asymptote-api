"""FAISS-based vector store with persistence."""

from pathlib import Path
from typing import List, Optional, Tuple
import json
import logging
import numpy as np
import faiss

from models.schemas import ChunkMetadata, SearchResult

logger = logging.getLogger(__name__)


class VectorStore:
    """FAISS-based vector store for similarity search with metadata persistence."""

    def __init__(self, index_dir: Path, embedding_dim: int = 384):
        """
        Initialize the vector store.

        Args:
            index_dir: Directory to store FAISS index and metadata
            embedding_dim: Dimension of embedding vectors
        """
        # Use separate subdirectory for JSON storage to avoid conflicts with SQLite
        self.index_dir = index_dir / "json"
        self.index_dir.mkdir(parents=True, exist_ok=True)
        self.embedding_dim = embedding_dim

        self.index_path = self.index_dir / "faiss.index"
        self.metadata_path = self.index_dir / "metadata.json"
        self.embeddings_path = self.index_dir / "embeddings.npy"

        # FAISS index (using L2 distance, will convert to cosine similarity)
        self.index: Optional[faiss.Index] = None

        # Metadata storage: list of ChunkMetadata dicts
        self.metadata: List[dict] = []

        # Embeddings storage: NumPy array of embeddings
        self.embeddings: Optional[np.ndarray] = None

        # Document tracking
        self.document_map: dict[str, List[int]] = {}  # doc_id -> list of chunk indices

        self._load_or_create_index()

    def _load_or_create_index(self):
        """Load existing index from disk or create a new one."""
        if self.index_path.exists() and self.metadata_path.exists():
            logger.info("Loading existing FAISS index")
            self.index = faiss.read_index(str(self.index_path))
            with open(self.metadata_path, "r", encoding="utf-8") as f:
                self.metadata = json.load(f)

            # Load embeddings if they exist
            if self.embeddings_path.exists():
                self.embeddings = np.load(str(self.embeddings_path))
                logger.info(f"Loaded embeddings array with shape {self.embeddings.shape}")
            else:
                logger.warning("Embeddings file not found - deletion will not work properly")
                self.embeddings = None

            # Rebuild document map
            self._rebuild_document_map()

            logger.info(f"Loaded index with {len(self.metadata)} chunks")
        else:
            logger.info("Creating new FAISS index")
            # Use IndexFlatIP for cosine similarity (inner product)
            # Vectors must be L2 normalized before adding
            self.index = faiss.IndexFlatIP(self.embedding_dim)
            self.metadata = []
            self.embeddings = None
            self.document_map = {}

    def _rebuild_document_map(self):
        """Rebuild the document map from metadata."""
        self.document_map = {}
        for idx, chunk in enumerate(self.metadata):
            doc_id = chunk["document_id"]
            if doc_id not in self.document_map:
                self.document_map[doc_id] = []
            self.document_map[doc_id].append(idx)

    def load(self):
        """Reload the index from disk (public method for external reload)."""
        logger.info("Reloading index from disk...")
        self._load_or_create_index()
        logger.info(f"Reload complete. Total chunks: {len(self.metadata)}")

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

        # Add metadata
        start_idx = len(self.metadata)
        for idx, chunk in enumerate(chunks):
            chunk_dict = chunk.model_dump()
            self.metadata.append(chunk_dict)

            # Update document map
            doc_id = chunk.document_id
            if doc_id not in self.document_map:
                self.document_map[doc_id] = []
            self.document_map[doc_id].append(start_idx + idx)

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

            chunk = self.metadata[idx]
            result = SearchResult(
                filename=chunk["filename"],
                page_number=chunk["page_number"],
                text_snippet=chunk["text"],
                similarity_score=float(similarity),  # Already cosine similarity due to IP with normalized vectors
                document_id=chunk["document_id"],
                chunk_id=chunk["chunk_id"],
                pdf_url="",  # Will be populated by the API endpoint
                page_url="",  # Will be populated by the API endpoint
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
        if document_id not in self.document_map:
            logger.warning(f"Document {document_id} not found in index")
            return 0

        # Get indices to delete
        indices_to_delete = set(self.document_map[document_id])
        num_deleted = len(indices_to_delete)

        logger.info(f"Deleting {num_deleted} chunks for document {document_id}")

        # Create new metadata and embeddings without deleted chunks
        new_metadata = []
        new_embeddings = []

        for idx, chunk in enumerate(self.metadata):
            if idx not in indices_to_delete:
                new_metadata.append(chunk)
                if self.embeddings is not None:
                    new_embeddings.append(self.embeddings[idx])

        # Rebuild index (FAISS doesn't support efficient deletion)
        logger.info(f"Rebuilding index with {len(new_metadata)} remaining chunks")
        self.metadata = new_metadata

        # Rebuild FAISS index with remaining embeddings
        self.index = faiss.IndexFlatIP(self.embedding_dim)

        if len(new_embeddings) > 0:
            self.embeddings = np.array(new_embeddings, dtype=np.float32)
            self.index.add(self.embeddings)
            logger.info(f"Re-added {len(new_embeddings)} vectors to index")
        else:
            self.embeddings = None
            logger.info("Index is now empty")

        # Rebuild document map
        self._rebuild_document_map()

        logger.info(f"Successfully deleted document {document_id}")

        return num_deleted

    def list_documents(self) -> List[dict]:
        """
        List all indexed documents with their metadata.

        Returns:
            List of document metadata dictionaries
        """
        doc_stats = {}

        for chunk in self.metadata:
            doc_id = chunk["document_id"]
            if doc_id not in doc_stats:
                doc_stats[doc_id] = {
                    "document_id": doc_id,
                    "filename": chunk["filename"],
                    "total_chunks": 0,
                    "pages": set(),
                }

            doc_stats[doc_id]["total_chunks"] += 1
            doc_stats[doc_id]["pages"].add(chunk["page_number"])

        # Convert to list and add page count
        documents = []
        for doc_id, stats in doc_stats.items():
            documents.append({
                "document_id": doc_id,
                "filename": stats["filename"],
                "total_pages": len(stats["pages"]),
                "total_chunks": stats["total_chunks"],
            })

        return documents

    def save(self):
        """Persist the index, embeddings, and metadata to disk."""
        logger.info(f"Saving index with {len(self.metadata)} chunks")
        faiss.write_index(self.index, str(self.index_path))

        with open(self.metadata_path, "w", encoding="utf-8") as f:
            json.dump(self.metadata, f, indent=2)

        # Save embeddings
        if self.embeddings is not None:
            np.save(str(self.embeddings_path), self.embeddings)
            logger.info(f"Saved embeddings array with shape {self.embeddings.shape}")

        logger.info("Index saved successfully")

    def get_total_chunks(self) -> int:
        """Get the total number of chunks in the index."""
        return len(self.metadata)

    def clear_index(self):
        """Clear all data from the index."""
        logger.info("Clearing vector store index and metadata")

        # Create new empty FAISS index
        self.index = faiss.IndexFlatIP(self.embedding_dim)
        self.metadata = []
        self.embeddings = None
        self.document_map = {}

        # Save the empty index
        self.save()

        logger.info("Vector store cleared successfully")
