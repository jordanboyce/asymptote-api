"""Re-indexing service for batch document processing.

Handles:
- Background re-indexing of all documents (global or per-collection)
- Progress tracking
- Configuration snapshot for consistent indexing
"""

import logging
import asyncio
from pathlib import Path
from typing import Optional, List, Callable
from services.app_database import app_db
from services.document_extractor import DocumentExtractor
from services.chunker import TextChunker
from services.embedder import EmbeddingService
from services.vector_store import VectorStore
from models.schemas import ChunkMetadata

logger = logging.getLogger(__name__)


class ReindexService:
    """Manages document re-indexing operations."""

    def __init__(self):
        self.current_job_id: Optional[int] = None
        self.current_collection_id: Optional[str] = None
        self.is_running = False
        self.reload_callback: Optional[Callable[[str], None]] = None  # Takes collection_id

    async def start_collection_reindex(
        self,
        collection_id: str,
        documents_dir: Path,
        indexes_dir: Path,
        embedding_model: str,
        chunk_size: int,
        chunk_overlap: int,
        embedding_dim: int = 384,
    ) -> int:
        """Start a re-indexing job for a specific collection.

        Args:
            collection_id: Collection to reindex
            documents_dir: Directory containing documents to index
            indexes_dir: Directory for storing indexes
            embedding_model: Embedding model to use
            chunk_size: Chunk size for text splitting
            chunk_overlap: Overlap between chunks
            embedding_dim: Embedding dimensions

        Returns:
            Job ID for tracking progress

        Raises:
            RuntimeError: If a re-indexing job is already running
        """
        # Check if already running
        active_job = app_db.get_active_reindex_job()
        if active_job:
            raise RuntimeError(
                f"Re-indexing job {active_job['id']} is already running"
            )

        # Create job record with collection info
        config_snapshot = {
            "collection_id": collection_id,
            "embedding_model": embedding_model,
            "chunk_size": chunk_size,
            "chunk_overlap": chunk_overlap,
        }

        job_id = app_db.create_reindex_job(config_snapshot)

        # Start background task
        asyncio.create_task(self._run_collection_reindex(
            job_id=job_id,
            collection_id=collection_id,
            documents_dir=documents_dir,
            indexes_dir=indexes_dir,
            embedding_model=embedding_model,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            embedding_dim=embedding_dim,
        ))

        return job_id

    async def _run_collection_reindex(
        self,
        job_id: int,
        collection_id: str,
        documents_dir: Path,
        indexes_dir: Path,
        embedding_model: str,
        chunk_size: int,
        chunk_overlap: int,
        embedding_dim: int,
    ):
        """Run the re-indexing process for a collection in background.

        Args:
            job_id: Job ID for tracking
            collection_id: Collection being reindexed
            documents_dir: Directory with documents
            indexes_dir: Directory for indexes
            embedding_model: Model name
            chunk_size: Characters per chunk
            chunk_overlap: Overlap size
            embedding_dim: Embedding dimensions
        """
        try:
            self.is_running = True
            self.current_job_id = job_id
            self.current_collection_id = collection_id

            # Update job status
            app_db.update_reindex_job(job_id, status="running")

            # Get list of documents
            supported_extensions = {".pdf", ".txt", ".docx", ".csv", ".md", ".json"}
            documents = [
                f for f in documents_dir.glob("*")
                if f.is_file() and f.suffix.lower() in supported_extensions
            ]

            total_docs = len(documents)
            app_db.update_reindex_job(job_id, total_documents=total_docs)

            if total_docs == 0:
                app_db.update_reindex_job(
                    job_id,
                    status="completed",
                    processed_documents=0
                )
                return

            # Initialize services with new config
            embedding_service = EmbeddingService(model_name=embedding_model)
            text_chunker = TextChunker(
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap
            )
            document_extractor = DocumentExtractor()

            # Create new vector store in collection's indexes directory
            vector_store = VectorStore(
                index_dir=indexes_dir,
                embedding_dim=embedding_service.embedding_dim
            )

            # Clear existing index
            logger.info(f"Clearing existing index for collection {collection_id} (job {job_id})")
            vector_store.clear_index()

            # Process each document
            for idx, doc_path in enumerate(documents, 1):
                try:
                    # Update progress
                    app_db.update_reindex_job(
                        job_id,
                        current_file=doc_path.name,
                        processed_documents=idx - 1
                    )

                    logger.info(f"Re-indexing ({idx}/{total_docs}): {doc_path.name}")

                    # Extract text
                    pages = document_extractor.extract_text(doc_path)
                    if not pages:
                        logger.warning(f"No text extracted from {doc_path.name}")
                        continue

                    # Generate document ID from content
                    import hashlib
                    with open(doc_path, "rb") as f:
                        doc_id = hashlib.sha256(f.read()).hexdigest()[:16]

                    # Chunk and embed using the proper chunker method
                    chunk_metadata_list = text_chunker.chunk_document(
                        page_texts=pages,
                        document_id=doc_id,
                        filename=doc_path.name
                    )

                    if not chunk_metadata_list:
                        logger.warning(f"No chunks created from {doc_path.name}")
                        continue

                    # Generate embeddings
                    texts = [chunk.text for chunk in chunk_metadata_list]
                    embeddings = embedding_service.embed_texts(texts)

                    # Add to index using add_chunks (the correct method)
                    vector_store.add_chunks(chunk_metadata_list, embeddings)

                    logger.info(
                        f"Indexed {doc_path.name}: "
                        f"{len(pages)} pages, {len(chunk_metadata_list)} chunks"
                    )

                except Exception as e:
                    logger.error(f"Failed to process {doc_path.name}: {e}")
                    continue

                # Yield control to allow other async operations (like status checks)
                await asyncio.sleep(0)

            # Save the index to disk
            logger.info("Saving re-indexed data to disk...")
            vector_store.save()

            # Mark as completed
            app_db.update_reindex_job(
                job_id,
                status="completed",
                processed_documents=total_docs,
                current_file=None
            )

            logger.info(f"Re-indexing job {job_id} for collection {collection_id} completed successfully")

            # Trigger reload callback to refresh the indexer for this collection
            if self.reload_callback:
                try:
                    self.reload_callback(collection_id)
                    logger.info(f"Collection {collection_id} indexer reloaded successfully")
                except Exception as e:
                    logger.error(f"Failed to reload indexer for collection {collection_id}: {e}")

        except Exception as e:
            logger.error(f"Re-indexing job {job_id} failed: {e}")
            app_db.update_reindex_job(
                job_id,
                status="failed",
                error=str(e)
            )

        finally:
            self.is_running = False
            self.current_job_id = None
            self.current_collection_id = None

    async def start_reindex(
        self,
        documents_dir: Path,
        embedding_model: str,
        chunk_size: int,
        chunk_overlap: int,
        embedding_dim: int = 384,
    ) -> int:
        """Start a re-indexing job.

        Args:
            documents_dir: Directory containing documents to index
            embedding_model: Embedding model to use
            chunk_size: Chunk size for text splitting
            chunk_overlap: Overlap between chunks
            embedding_dim: Embedding dimensions

        Returns:
            Job ID for tracking progress

        Raises:
            RuntimeError: If a re-indexing job is already running
        """
        # Check if already running
        active_job = app_db.get_active_reindex_job()
        if active_job:
            raise RuntimeError(
                f"Re-indexing job {active_job['id']} is already running"
            )

        # Create job record
        config_snapshot = {
            "embedding_model": embedding_model,
            "chunk_size": chunk_size,
            "chunk_overlap": chunk_overlap,
        }

        job_id = app_db.create_reindex_job(config_snapshot)

        # Start background task
        asyncio.create_task(self._run_reindex(
            job_id=job_id,
            documents_dir=documents_dir,
            embedding_model=embedding_model,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            embedding_dim=embedding_dim,
        ))

        return job_id

    async def _run_reindex(
        self,
        job_id: int,
        documents_dir: Path,
        embedding_model: str,
        chunk_size: int,
        chunk_overlap: int,
        embedding_dim: int,
    ):
        """Run the re-indexing process in background.

        Args:
            job_id: Job ID for tracking
            documents_dir: Directory with documents
            embedding_model: Model name
            chunk_size: Characters per chunk
            chunk_overlap: Overlap size
            embedding_dim: Embedding dimensions
        """
        try:
            self.is_running = True
            self.current_job_id = job_id

            # Update job status
            app_db.update_reindex_job(job_id, status="running")

            # Get list of documents
            supported_extensions = {".pdf", ".txt", ".docx", ".csv", ".md", ".json"}
            documents = [
                f for f in documents_dir.glob("*")
                if f.is_file() and f.suffix.lower() in supported_extensions
            ]

            total_docs = len(documents)
            app_db.update_reindex_job(job_id, total_documents=total_docs)

            if total_docs == 0:
                app_db.update_reindex_job(
                    job_id,
                    status="completed",
                    processed_documents=0
                )
                return

            # Initialize services with new config
            embedding_service = EmbeddingService(model_name=embedding_model)
            text_chunker = TextChunker(
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap
            )
            document_extractor = DocumentExtractor()

            # Create new vector store
            indexes_dir = documents_dir.parent / "indexes"
            vector_store = VectorStore(
                index_dir=indexes_dir,
                embedding_dim=embedding_service.embedding_dim
            )

            # Clear existing index
            logger.info(f"Clearing existing index for re-indexing job {job_id}")
            vector_store.clear_index()

            # Process each document
            for idx, doc_path in enumerate(documents, 1):
                try:
                    # Update progress
                    app_db.update_reindex_job(
                        job_id,
                        current_file=doc_path.name,
                        processed_documents=idx - 1
                    )

                    logger.info(f"Re-indexing ({idx}/{total_docs}): {doc_path.name}")

                    # Extract text
                    pages = document_extractor.extract_text(doc_path)
                    if not pages:
                        logger.warning(f"No text extracted from {doc_path.name}")
                        continue

                    # Generate document ID from content
                    import hashlib
                    with open(doc_path, "rb") as f:
                        doc_id = hashlib.sha256(f.read()).hexdigest()[:16]

                    # Chunk and embed using the proper chunker method
                    chunk_metadata_list = text_chunker.chunk_document(
                        page_texts=pages,
                        document_id=doc_id,
                        filename=doc_path.name
                    )

                    if not chunk_metadata_list:
                        logger.warning(f"No chunks created from {doc_path.name}")
                        continue

                    # Generate embeddings
                    texts = [chunk.text for chunk in chunk_metadata_list]
                    embeddings = embedding_service.embed_texts(texts)

                    # Add to index using add_chunks (the correct method)
                    vector_store.add_chunks(chunk_metadata_list, embeddings)

                    logger.info(
                        f"Indexed {doc_path.name}: "
                        f"{len(pages)} pages, {len(chunk_metadata_list)} chunks"
                    )

                except Exception as e:
                    logger.error(f"Failed to process {doc_path.name}: {e}")
                    continue

                # Yield control to allow other async operations (like status checks)
                await asyncio.sleep(0)

            # Save the index to disk
            logger.info("Saving re-indexed data to disk...")
            vector_store.save()

            # Mark as completed
            app_db.update_reindex_job(
                job_id,
                status="completed",
                processed_documents=total_docs,
                current_file=None
            )

            logger.info(f"Re-indexing job {job_id} completed successfully")

            # Trigger reload callback to refresh the main indexer
            if self.reload_callback:
                try:
                    self.reload_callback()
                    logger.info("Main indexer reloaded successfully")
                except Exception as e:
                    logger.error(f"Failed to reload main indexer: {e}")

        except Exception as e:
            logger.error(f"Re-indexing job {job_id} failed: {e}")
            app_db.update_reindex_job(
                job_id,
                status="failed",
                error=str(e)
            )

        finally:
            self.is_running = False
            self.current_job_id = None

    def get_job_status(self, job_id: int) -> Optional[dict]:
        """Get status of a re-indexing job.

        Args:
            job_id: Job ID

        Returns:
            Job details with progress information
        """
        return app_db.get_reindex_job(job_id)

    def get_current_job(self) -> Optional[dict]:
        """Get currently active re-indexing job.

        Returns:
            Active job details or None
        """
        return app_db.get_active_reindex_job()


# Global instance
reindex_service = ReindexService()
