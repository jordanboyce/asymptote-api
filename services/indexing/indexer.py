"""Document indexing orchestration service."""

from pathlib import Path
from typing import List, Optional
import hashlib
import logging
from datetime import datetime

from config import settings
from models.schemas import (
    DocumentMetadata,
    AIOptions,
    AIUsage,
    AIUsageDetail,
)
from services.document_extractor import DocumentExtractor, ExtractionResult
from services.chunker import TextChunker
from services.embedder import EmbeddingService
from services.vector_store import VectorStore

logger = logging.getLogger(__name__)


class DocumentIndexer:
    """Orchestrates the document indexing pipeline."""

    def __init__(
        self,
        vector_store: VectorStore,
        embedding_service: EmbeddingService,
        document_extractor: DocumentExtractor,
        text_chunker: TextChunker,
    ):
        """
        Initialize the document indexer.

        Args:
            vector_store: Vector store instance
            embedding_service: Embedding service instance
            document_extractor: Document extractor instance (supports PDF, TXT, DOCX, CSV)
            text_chunker: Text chunker instance
        """
        self.vector_store = vector_store
        self.embedding_service = embedding_service
        self.document_extractor = document_extractor
        self.text_chunker = text_chunker

    def index_document(self, document_path: Path, filename: str) -> DocumentMetadata:
        """
        Index a single document (PDF, TXT, DOCX, CSV, MD, or JSON).

        Args:
            document_path: Path to the document file
            filename: Original filename

        Returns:
            DocumentMetadata object
        """
        logger.info(f"Indexing document: {filename}")

        # Generate document ID from file content hash
        document_id = self._generate_document_id(document_path)

        # Determine source format from file extension
        source_format = document_path.suffix.lower().lstrip(".")

        # Handle CSV with row-level indexing (v3.0 feature)
        if source_format == "csv" and settings.csv_row_level_indexing:
            return self._index_csv_rows(document_path, filename, document_id)

        # Extract text from document
        logger.debug(f"Extracting text from {filename}")
        extraction_result = self.document_extractor.extract_text(document_path)

        # Handle ExtractionResult object
        if isinstance(extraction_result, ExtractionResult):
            page_texts = extraction_result.page_texts
            extraction_method = extraction_result.method
        else:
            # Backward compatibility: plain dict
            page_texts = extraction_result
            extraction_method = "text"

        num_pages = len(page_texts)

        if num_pages == 0:
            logger.warning(f"No pages extracted from {filename}")
            raise ValueError(f"Could not extract any pages from {filename}")

        # Chunk the text with format metadata
        logger.debug(f"Chunking text from {filename}")
        chunks = self.text_chunker.chunk_document(
            page_texts=page_texts,
            document_id=document_id,
            filename=filename,
            source_format=source_format,
            extraction_method=extraction_method,
        )

        num_chunks = len(chunks)
        if num_chunks == 0:
            logger.warning(f"No chunks created from {filename}")
            raise ValueError(f"Could not create any chunks from {filename}")

        # Generate embeddings
        logger.debug(f"Generating embeddings for {num_chunks} chunks")
        chunk_texts = [chunk.text for chunk in chunks]
        embeddings = self.embedding_service.embed_texts(chunk_texts)

        # Add to vector store
        logger.debug(f"Adding {num_chunks} chunks to vector store")
        self.vector_store.add_chunks(chunks, embeddings)

        # Create metadata with v3.0 fields
        metadata = DocumentMetadata(
            document_id=document_id,
            filename=filename,
            total_pages=num_pages,
            total_chunks=num_chunks,
            indexed_at=datetime.utcnow().isoformat(),
            source_format=source_format,
            extraction_method=extraction_method,
            embedding_model=settings.embedding_model,
            chunk_size=settings.chunk_size,
            chunk_overlap=settings.chunk_overlap,
        )

        logger.info(
            f"Successfully indexed {filename}: {num_pages} pages, {num_chunks} chunks "
            f"(format={source_format}, method={extraction_method})"
        )
        return metadata

    def _index_csv_rows(self, document_path: Path, filename: str,
                        document_id: str) -> DocumentMetadata:
        """
        Index a CSV file with row-level chunking (v3.0 feature).

        Args:
            document_path: Path to CSV file
            filename: Original filename
            document_id: Generated document ID

        Returns:
            DocumentMetadata object
        """
        logger.info(f"Indexing CSV with row-level chunking: {filename}")

        # Extract CSV rows with column metadata
        csv_rows = self.document_extractor.extract_csv_rows(document_path)

        if not csv_rows:
            logger.warning(f"No rows extracted from {filename}")
            raise ValueError(f"Could not extract any rows from {filename}")

        num_rows = len(csv_rows)

        # Create chunks from CSV rows
        chunks = self.text_chunker.chunk_csv_rows(
            csv_rows=csv_rows,
            document_id=document_id,
            filename=filename,
            rows_per_chunk=settings.csv_rows_per_chunk if not settings.csv_row_level_indexing else 1,
        )

        num_chunks = len(chunks)

        # Generate embeddings
        logger.debug(f"Generating embeddings for {num_chunks} CSV row chunks")
        chunk_texts = [chunk.text for chunk in chunks]
        embeddings = self.embedding_service.embed_texts(chunk_texts)

        # Add to vector store
        logger.debug(f"Adding {num_chunks} CSV chunks to vector store")
        self.vector_store.add_chunks(chunks, embeddings)

        # Create metadata
        metadata = DocumentMetadata(
            document_id=document_id,
            filename=filename,
            total_pages=num_rows,  # For CSV, "pages" = rows
            total_chunks=num_chunks,
            indexed_at=datetime.utcnow().isoformat(),
            source_format="csv",
            extraction_method="text",
            embedding_model=settings.embedding_model,
            chunk_size=settings.chunk_size,
            chunk_overlap=settings.chunk_overlap,
        )

        logger.info(f"Successfully indexed CSV {filename}: {num_rows} rows, {num_chunks} chunks")
        return metadata

    def search(
        self,
        query: str,
        top_k: int = 10,
        ai_service=None,
        ai_options: Optional[AIOptions] = None,
    ) -> dict:
        """
        Search for documents matching the query, with optional AI enhancements.

        Args:
            query: Search query text
            top_k: Number of results to return
            ai_service: Optional AIService instance (created from user's API key)
            ai_options: Optional AI feature flags

        Returns:
            Dict with 'results', and optionally 'enhanced_query', 'synthesis', 'ai_usage'
        """
        logger.info(f"Searching for: {query[:100]}")

        ai_active = ai_service and ai_options
        ai_usage = AIUsage() if ai_active else None
        synthesis = None

        # Step 1: Generate query embedding and search
        query_embedding = self.embedding_service.embed_query(query)

        # Fetch extra results if reranking (so the LLM has a bigger pool)
        fetch_k = min(top_k * 5, 50) if (ai_active and ai_options.rerank) else top_k
        results = self.vector_store.search(query_embedding, top_k=fetch_k)

        # Step 3: Optionally rerank results
        if ai_active and ai_options.rerank and len(results) > 0:
            try:
                rerank_input = [
                    {
                        "index": i,
                        "filename": r.filename,
                        "text_snippet": r.text_snippet,
                        "similarity_score": r.similarity_score,
                    }
                    for i, r in enumerate(results)
                ]
                rerank_result = ai_service.rerank_results(query, rerank_input, top_k)
                usage = rerank_result["usage"]

                if usage:
                    ai_usage.features_used.append("reranking")
                    ai_usage.reranking = AIUsageDetail(**usage)
                    ai_usage.total_input_tokens += usage["input_tokens"]
                    ai_usage.total_output_tokens += usage["output_tokens"]

                # Reorder results based on AI ranking
                valid_indices = [
                    i for i in rerank_result["reranked_indices"]
                    if 0 <= i < len(results)
                ]
                results = [results[i] for i in valid_indices] if valid_indices else results[:top_k]
            except Exception as e:
                logger.warning(f"Reranking failed, using original order: {e}")
                results = results[:top_k]
        else:
            results = results[:top_k]

        # Step 4: Optionally synthesize an answer from results
        if ai_active and ai_options.synthesize and len(results) > 0:
            try:
                synth_input = [
                    {
                        "filename": r.filename,
                        "page_number": r.page_number,
                        "text_snippet": r.text_snippet,
                    }
                    for r in results
                ]
                synth_result = ai_service.synthesize_results(query, synth_input)
                synthesis = synth_result["synthesis"]
                usage = synth_result["usage"]

                if usage:
                    ai_usage.features_used.append("synthesis")
                    ai_usage.synthesis = AIUsageDetail(**usage)
                    ai_usage.total_input_tokens += usage["input_tokens"]
                    ai_usage.total_output_tokens += usage["output_tokens"]
            except Exception as e:
                logger.warning(f"Synthesis failed: {e}")

        logger.info(f"Found {len(results)} results")

        return {
            "results": results,
            "synthesis": synthesis,
            "ai_usage": ai_usage,
        }

    def list_documents(self) -> List[dict]:
        """
        List all indexed documents.

        Returns:
            List of document metadata dictionaries
        """
        return self.vector_store.list_documents()

    def delete_document(self, document_id: str) -> int:
        """
        Delete a document from the index.

        Args:
            document_id: Document ID to delete

        Returns:
            Number of chunks deleted
        """
        logger.info(f"Deleting document: {document_id}")
        num_deleted = self.vector_store.delete_document(document_id)
        logger.info(f"Deleted {num_deleted} chunks")
        return num_deleted

    def save_index(self):
        """Persist the vector store to disk."""
        self.vector_store.save()

    def _generate_document_id(self, document_path: Path) -> str:
        """
        Generate a unique document ID based on file content.

        Args:
            document_path: Path to the document file

        Returns:
            Document ID (SHA256 hash)
        """
        hasher = hashlib.sha256()
        with open(document_path, "rb") as f:
            # Read file in chunks to handle large files
            for chunk in iter(lambda: f.read(8192), b""):
                hasher.update(chunk)

        return hasher.hexdigest()[:16]  # Use first 16 characters
