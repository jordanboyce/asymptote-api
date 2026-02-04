"""Document indexing orchestration service."""

from pathlib import Path
from typing import List
import hashlib
import logging
from datetime import datetime

from models.schemas import DocumentMetadata, ChunkMetadata, SearchResult
from services.document_extractor import DocumentExtractor
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
        Index a single document (PDF, TXT, DOCX, or CSV).

        Args:
            document_path: Path to the document file
            filename: Original filename

        Returns:
            DocumentMetadata object
        """
        logger.info(f"Indexing document: {filename}")

        # Generate document ID from file content hash
        document_id = self._generate_document_id(document_path)

        # Extract text from document
        logger.debug(f"Extracting text from {filename}")
        page_texts = self.document_extractor.extract_text(document_path)
        num_pages = len(page_texts)

        if num_pages == 0:
            logger.warning(f"No pages extracted from {filename}")
            raise ValueError(f"Could not extract any pages from {filename}")

        # Chunk the text
        logger.debug(f"Chunking text from {filename}")
        chunks = self.text_chunker.chunk_document(
            page_texts=page_texts,
            document_id=document_id,
            filename=filename,
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

        # Create metadata
        metadata = DocumentMetadata(
            document_id=document_id,
            filename=filename,
            total_pages=num_pages,
            total_chunks=num_chunks,
            indexed_at=datetime.utcnow().isoformat(),
        )

        logger.info(f"Successfully indexed {filename}: {num_pages} pages, {num_chunks} chunks")
        return metadata

    def search(self, query: str, top_k: int = 10) -> List[SearchResult]:
        """
        Search for documents matching the query.

        Args:
            query: Search query text
            top_k: Number of results to return

        Returns:
            List of SearchResult objects
        """
        logger.info(f"Searching for: {query[:100]}")

        # Generate query embedding
        query_embedding = self.embedding_service.embed_query(query)

        # Search vector store
        results = self.vector_store.search(query_embedding, top_k=top_k)

        logger.info(f"Found {len(results)} results")
        return results

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
