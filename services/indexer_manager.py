"""Manages DocumentIndexer instances for each collection.

Each collection has its own:
- Vector store (FAISS index + metadata)
- Document directory
- Settings (chunk size, overlap, embedding model)
"""

import logging
from pathlib import Path
from typing import Dict, Optional

from services.collection_service import collection_service
from services.document_extractor import DocumentExtractor
from services.chunker import TextChunker
from services.embedder import EmbeddingService
from services.vector_store import VectorStore
from services.vector_store_v2 import VectorStoreV2
from services.indexing import DocumentIndexer
from config import settings

logger = logging.getLogger(__name__)


class IndexerManager:
    """Manages DocumentIndexer instances for multiple collections."""

    def __init__(self):
        """Initialize the indexer manager."""
        self._indexers: Dict[str, DocumentIndexer] = {}
        self._embedding_services: Dict[str, EmbeddingService] = {}

        # v3.0: Initialize document extractor with OCR settings
        self._document_extractor = DocumentExtractor(
            enable_ocr=settings.enable_ocr,
            ocr_engine=settings.ocr_engine,
            ocr_language=settings.ocr_language,
            ocr_fallback_only=settings.ocr_fallback_only,
        )

        if settings.enable_ocr:
            ocr_available = self._document_extractor.is_ocr_available()
            logger.info(f"OCR enabled: {ocr_available} (engine: {settings.ocr_engine})")

    def get_indexer(self, collection_id: str = "default") -> DocumentIndexer:
        """Get or create an indexer for a collection.

        Args:
            collection_id: Collection ID (default: "default")

        Returns:
            DocumentIndexer instance for the collection
        """
        if collection_id in self._indexers:
            return self._indexers[collection_id]

        # Get collection settings
        collection = collection_service.get_collection(collection_id)
        if not collection:
            raise ValueError(f"Collection '{collection_id}' not found")

        # Create indexer for this collection
        indexer = self._create_indexer(collection)
        self._indexers[collection_id] = indexer

        logger.info(f"Created indexer for collection '{collection_id}'")
        return indexer

    def _create_indexer(self, collection: dict) -> DocumentIndexer:
        """Create a DocumentIndexer for a collection.

        Args:
            collection: Collection settings dict

        Returns:
            DocumentIndexer instance
        """
        collection_id = collection["id"]
        embedding_model = collection.get("embedding_model", settings.embedding_model)
        chunk_size = collection.get("chunk_size", settings.chunk_size)
        chunk_overlap = collection.get("chunk_overlap", settings.chunk_overlap)

        # Get or create embedding service for this model
        if embedding_model not in self._embedding_services:
            logger.info(f"Loading embedding model: {embedding_model}")
            self._embedding_services[embedding_model] = EmbeddingService(
                model_name=embedding_model
            )
        embedding_service = self._embedding_services[embedding_model]

        # Get paths for this collection
        indexes_dir = collection_service.get_indexes_path(collection_id)

        # Create vector store
        if settings.metadata_storage.lower() == "sqlite":
            vector_store = VectorStoreV2(
                index_dir=indexes_dir,
                embedding_dim=embedding_service.embedding_dim,
            )
        else:
            vector_store = VectorStore(
                index_dir=indexes_dir,
                embedding_dim=embedding_service.embedding_dim,
            )

        # Create text chunker with collection settings
        text_chunker = TextChunker(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )

        # Create indexer
        return DocumentIndexer(
            vector_store=vector_store,
            embedding_service=embedding_service,
            document_extractor=self._document_extractor,
            text_chunker=text_chunker,
        )

    def reload_indexer(self, collection_id: str = "default"):
        """Reload an indexer's vector store from disk.

        Args:
            collection_id: Collection ID
        """
        if collection_id in self._indexers:
            self._indexers[collection_id].vector_store.load()
            logger.info(f"Reloaded indexer for collection '{collection_id}'")

    def invalidate_indexer(self, collection_id: str):
        """Remove a cached indexer (e.g., after settings change).

        Args:
            collection_id: Collection ID
        """
        if collection_id in self._indexers:
            # Save before removing
            self._indexers[collection_id].save_index()
            del self._indexers[collection_id]
            logger.info(f"Invalidated indexer for collection '{collection_id}'")

    def remove_indexer(self, collection_id: str):
        """Remove a cached indexer without saving (e.g., after collection deletion).

        Args:
            collection_id: Collection ID
        """
        if collection_id in self._indexers:
            del self._indexers[collection_id]
            logger.info(f"Removed indexer for deleted collection '{collection_id}'")

    def close_indexer(self, collection_id: str):
        """Close an indexer and release all resources (e.g., before restore).

        This properly closes database connections and clears references
        to allow file deletion on Windows.

        Args:
            collection_id: Collection ID
        """
        if collection_id in self._indexers:
            indexer = self._indexers[collection_id]
            # Close the vector store to release file handles
            if hasattr(indexer.vector_store, 'close'):
                indexer.vector_store.close()
            del self._indexers[collection_id]
            logger.info(f"Closed indexer for collection '{collection_id}'")

    def save_all(self):
        """Save all indexers to disk."""
        for collection_id, indexer in self._indexers.items():
            try:
                indexer.save_index()
                logger.info(f"Saved index for collection '{collection_id}'")
            except Exception as e:
                logger.error(f"Failed to save index for '{collection_id}': {e}")

    def get_documents_path(self, collection_id: str = "default") -> Path:
        """Get the documents directory for a collection.

        Args:
            collection_id: Collection ID

        Returns:
            Path to documents directory
        """
        return collection_service.get_documents_path(collection_id)

    def get_indexes_path(self, collection_id: str = "default") -> Path:
        """Get the indexes directory for a collection.

        Args:
            collection_id: Collection ID

        Returns:
            Path to indexes directory
        """
        return collection_service.get_indexes_path(collection_id)

    def get_collection_stats(self, collection_id: str = "default") -> dict:
        """Get statistics for a collection.

        Args:
            collection_id: Collection ID

        Returns:
            Dict with document count, chunk count, etc.
        """
        try:
            indexer = self.get_indexer(collection_id)
            total_chunks = indexer.vector_store.get_total_chunks()
            documents = indexer.list_documents()

            return {
                "collection_id": collection_id,
                "total_documents": len(documents),
                "total_chunks": total_chunks,
                "total_pages": sum(d.get("total_pages", 0) or d.get("num_pages", 0) for d in documents),
            }
        except Exception as e:
            logger.error(f"Failed to get stats for '{collection_id}': {e}")
            return {
                "collection_id": collection_id,
                "total_documents": 0,
                "total_chunks": 0,
                "total_pages": 0,
            }


# Global instance
indexer_manager = IndexerManager()
