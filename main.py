"""
Asymptote API - Self-hosted semantic search for PDFs

Main application entry point.
"""

import logging
from contextlib import asynccontextmanager
from typing import List
from pathlib import Path
import shutil

from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from config import settings
from services.pdf_extractor import PDFExtractor
from services.chunker import TextChunker
from services.embedder import EmbeddingService
from services.vector_store import VectorStore
from services.vector_store_v2 import VectorStoreV2
from services.indexing import DocumentIndexer
from models.schemas import (
    UploadResponse,
    SearchRequest,
    SearchResponse,
    DocumentListResponse,
    DocumentMetadata,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


# Global services (initialized on startup)
_indexer: DocumentIndexer = None


def get_indexer() -> DocumentIndexer:
    """Dependency injection for indexer."""
    if _indexer is None:
        raise HTTPException(
            status_code=503,
            detail="Service is still initializing. Please wait a moment and try again."
        )
    return _indexer


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager - initialize and cleanup services."""
    global _indexer

    logger.info("Initializing Asymptote API...")

    # Initialize services
    logger.info("Loading embedding model...")
    embedding_service = EmbeddingService(model_name=settings.embedding_model)

    # Initialize vector store based on config
    logger.info(f"Initializing vector store (metadata: {settings.metadata_storage})...")
    if settings.metadata_storage.lower() == "sqlite":
        vector_store = VectorStoreV2(
            index_dir=settings.data_dir / "indexes",
            embedding_dim=embedding_service.embedding_dim,
        )
    else:
        vector_store = VectorStore(
            index_dir=settings.data_dir / "indexes",
            embedding_dim=embedding_service.embedding_dim,
        )

    pdf_extractor = PDFExtractor()
    text_chunker = TextChunker(
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
    )

    _indexer = DocumentIndexer(
        vector_store=vector_store,
        embedding_service=embedding_service,
        pdf_extractor=pdf_extractor,
        text_chunker=text_chunker,
    )

    logger.info("Asymptote API ready")
    logger.info(f"Data directory: {settings.data_dir}")
    logger.info(f"Embedding model: {settings.embedding_model}")
    logger.info(f"Metadata storage: {settings.metadata_storage}")
    logger.info(f"Indexed chunks: {vector_store.get_total_chunks()}")

    yield

    # Cleanup on shutdown
    logger.info("Shutting down Asymptote API...")
    _indexer.save_index()
    logger.info("Shutdown complete")


# Create FastAPI app
app = FastAPI(
    title="Asymptote API",
    description="Self-hosted semantic search for PDF documents",
    version="0.1.0",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Prepare PDF directory
pdf_dir = settings.data_dir / "pdfs"
pdf_dir.mkdir(parents=True, exist_ok=True)


# API Endpoints

@app.get("/", tags=["health"])
async def root():
    """Root endpoint - API health check."""
    return {
        "service": "Asymptote API",
        "status": "operational",
        "version": "0.1.0",
    }


@app.get("/health", tags=["health"])
async def health(indexer: DocumentIndexer = Depends(get_indexer)):
    """Health check endpoint."""
    total_chunks = indexer.vector_store.get_total_chunks() if indexer else 0
    return {
        "status": "healthy",
        "indexed_chunks": total_chunks,
    }


@app.post(
    "/documents/upload",
    response_model=UploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload and index PDF documents",
    tags=["documents"],
)
async def upload_documents(
    files: List[UploadFile] = File(...),
    indexer: DocumentIndexer = Depends(get_indexer)
) -> UploadResponse:
    """
    Upload one or more PDF files and automatically index their contents.

    Returns metadata about the indexed documents including page and chunk counts.
    """
    if not files:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No files provided",
        )

    # Validate all files are PDFs
    for file in files:
        if not file.filename.lower().endswith(".pdf"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File {file.filename} is not a PDF",
            )

    indexed_docs = []
    total_pages = 0
    total_chunks = 0

    for file in files:
        try:
            # Save uploaded file
            file_path = pdf_dir / file.filename
            with open(file_path, "wb") as f:
                shutil.copyfileobj(file.file, f)

            logger.info(f"Saved uploaded file: {file.filename}")

            # Index the document
            doc_metadata = indexer.index_document(file_path, file.filename)

            indexed_docs.append(doc_metadata.document_id)
            total_pages += doc_metadata.num_pages
            total_chunks += doc_metadata.num_chunks

        except Exception as e:
            logger.error(f"Failed to index {file.filename}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to index {file.filename}: {str(e)}",
            )

    # Persist the index
    indexer.save_index()

    return UploadResponse(
        message=f"Successfully indexed {len(indexed_docs)} document(s)",
        documents_processed=len(indexed_docs),
        total_pages=total_pages,
        total_chunks=total_chunks,
        document_ids=indexed_docs,
    )


@app.post(
    "/search",
    response_model=SearchResponse,
    summary="Search indexed documents",
    tags=["documents"],
)
async def search_documents(
    search_request: SearchRequest,
    request: Request,
    indexer: DocumentIndexer = Depends(get_indexer)
) -> SearchResponse:
    """
    Perform semantic similarity search over indexed documents.

    Returns ranked results with filename, page number, text snippet, and similarity score.
    """
    try:
        results = indexer.search(search_request.query, top_k=search_request.top_k)

        # Add URLs to each result
        base_url = str(request.base_url).rstrip('/')
        for result in results:
            result.pdf_url = f"{base_url}/documents/{result.document_id}/pdf"
            result.page_url = f"{base_url}/documents/{result.document_id}/pdf#page={result.page_number}"

        return SearchResponse(
            query=search_request.query,
            results=results,
            total_results=len(results),
        )

    except Exception as e:
        logger.error(f"Search failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Search failed: {str(e)}",
        )


@app.get(
    "/documents",
    response_model=DocumentListResponse,
    summary="List all indexed documents",
    tags=["documents"],
)
async def list_documents(
    indexer: DocumentIndexer = Depends(get_indexer)
) -> DocumentListResponse:
    """
    List all indexed documents with their metadata.

    Returns filename, page count, and chunk count for each document.
    """
    try:
        documents = indexer.list_documents()

        # Convert to DocumentMetadata objects
        doc_metadata_list = []
        for doc in documents:
            # Add placeholder timestamp (not tracked in current implementation)
            doc_metadata = DocumentMetadata(
                document_id=doc["document_id"],
                filename=doc["filename"],
                num_pages=doc["num_pages"],
                num_chunks=doc["num_chunks"],
                upload_timestamp="",  # Not tracked in vector store
            )
            doc_metadata_list.append(doc_metadata)

        return DocumentListResponse(
            documents=doc_metadata_list,
            total_documents=len(doc_metadata_list),
        )

    except Exception as e:
        logger.error(f"Failed to list documents: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list documents: {str(e)}",
        )


@app.get(
    "/documents/{document_id}/pdf",
    summary="Download PDF file",
    tags=["documents"],
    response_class=FileResponse,
)
async def get_pdf(
    document_id: str,
    indexer: DocumentIndexer = Depends(get_indexer)
):
    """
    Download the PDF file for a specific document.

    The URL can include #page=N to open at a specific page in the browser.
    """
    try:
        # Get document metadata to find filename
        documents = indexer.list_documents()
        doc = next((d for d in documents if d["document_id"] == document_id), None)

        if not doc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Document {document_id} not found",
            )

        # Find the PDF file
        pdf_path = pdf_dir / doc["filename"]

        if not pdf_path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"PDF file not found: {doc['filename']}",
            )

        return FileResponse(
            path=pdf_path,
            media_type="application/pdf",
            filename=doc["filename"],
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to retrieve PDF: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve PDF: {str(e)}",
        )


@app.delete(
    "/documents/{document_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete a document from the index",
    tags=["documents"],
)
async def delete_document(
    document_id: str,
    indexer: DocumentIndexer = Depends(get_indexer)
):
    """
    Remove a document and all its chunks from the index.

    Note: Current implementation has limitations - see vector_store.py for details.
    """
    try:
        num_deleted = indexer.delete_document(document_id)

        if num_deleted == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Document {document_id} not found",
            )

        # Persist the changes
        indexer.save_index()

        return {
            "message": f"Deleted document {document_id}",
            "chunks_deleted": num_deleted,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete document: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete document: {str(e)}",
        )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=True,
    )
