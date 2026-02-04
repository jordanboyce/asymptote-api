"""
Asymptote API - Self-hosted semantic search for documents

Main application entry point.
Supports PDF, TXT, DOCX, and CSV files.
"""

import logging
from contextlib import asynccontextmanager
from typing import List
from pathlib import Path
import shutil

from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from config import settings
from services.document_extractor import DocumentExtractor
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

    document_extractor = DocumentExtractor()
    text_chunker = TextChunker(
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
    )

    _indexer = DocumentIndexer(
        vector_store=vector_store,
        embedding_service=embedding_service,
        document_extractor=document_extractor,
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
    description="Self-hosted semantic search for documents (PDF, TXT, DOCX, CSV)",
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

# Prepare documents directory (supports PDF, TXT, DOCX, CSV)
document_dir = settings.data_dir / "documents"
document_dir.mkdir(parents=True, exist_ok=True)

# Prepare static directory
static_dir = Path(__file__).parent / "static"
static_dir.mkdir(exist_ok=True)


# Web Interface

@app.get("/", response_class=HTMLResponse, tags=["ui"])
async def web_interface():
    """Serve the web interface."""
    index_path = static_dir / "index.html"
    if index_path.exists():
        return HTMLResponse(content=index_path.read_text(encoding="utf-8"), status_code=200)
    else:
        return HTMLResponse(
            content="<h1>Asymptote API</h1><p>Web interface not found. Visit <a href='/docs'>/docs</a> for API documentation.</p>",
            status_code=200
        )


# API Endpoints

@app.get("/api", tags=["health"])
async def api_root():
    """API root endpoint."""
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
    summary="Upload and index documents (PDF, TXT, DOCX, CSV)",
    tags=["documents"],
)
async def upload_documents(
    files: List[UploadFile] = File(...),
    indexer: DocumentIndexer = Depends(get_indexer)
) -> UploadResponse:
    """
    Upload one or more documents and automatically index their contents.

    Supported formats: PDF, TXT, DOCX, CSV

    Returns metadata about the indexed documents including page and chunk counts.
    """
    if not files:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No files provided",
        )

    # Validate all files have supported extensions
    SUPPORTED_EXTENSIONS = {'.pdf', '.txt', '.docx', '.csv'}
    for file in files:
        file_ext = Path(file.filename).suffix.lower()
        if file_ext not in SUPPORTED_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File {file.filename} has unsupported type. Supported types: PDF, TXT, DOCX, CSV",
            )

    indexed_docs = []
    total_pages = 0
    total_chunks = 0

    for file in files:
        try:
            # Save uploaded file
            file_path = document_dir / file.filename
            with open(file_path, "wb") as f:
                shutil.copyfileobj(file.file, f)

            logger.info(f"Saved uploaded file: {file.filename}")

            # Index the document
            doc_metadata = indexer.index_document(file_path, file.filename)

            indexed_docs.append(doc_metadata.document_id)
            total_pages += doc_metadata.total_pages
            total_chunks += doc_metadata.total_chunks

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
            # Get timestamp from document file modification time
            doc_path = document_dir / doc["filename"]
            indexed_at = ""
            if doc_path.exists():
                from datetime import datetime
                mtime = doc_path.stat().st_mtime
                indexed_at = datetime.fromtimestamp(mtime).isoformat()

            doc_metadata = DocumentMetadata(
                document_id=doc["document_id"],
                filename=doc["filename"],
                total_pages=doc["total_pages"],
                total_chunks=doc["total_chunks"],
                indexed_at=indexed_at,
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
    summary="Download document file",
    tags=["documents"],
    response_class=FileResponse,
)
async def get_pdf(
    document_id: str,
    indexer: DocumentIndexer = Depends(get_indexer)
):
    """
    Download the document file for a specific document.

    For PDFs, the URL can include #page=N to open at a specific page in the browser.
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

        # Find the document file
        doc_path = document_dir / doc["filename"]

        if not doc_path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Document file not found: {doc['filename']}",
            )

        # Determine media type based on file extension
        file_ext = Path(doc["filename"]).suffix.lower()
        media_types = {
            '.pdf': 'application/pdf',
            '.txt': 'text/plain',
            '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            '.csv': 'text/csv',
        }
        media_type = media_types.get(file_ext, 'application/octet-stream')

        # Return file with inline display for PDFs, download for others
        disposition = 'inline' if file_ext == '.pdf' else 'attachment'
        return FileResponse(
            path=doc_path,
            media_type=media_type,
            headers={
                "Content-Disposition": f'{disposition}; filename="{doc["filename"]}"'
            }
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

    This will delete:
    - The document's metadata from the index
    - All chunks associated with the document
    - The document file from the data/documents directory
    """
    try:
        # Get document metadata before deletion to find the PDF filename
        documents = indexer.list_documents()
        doc = next((d for d in documents if d["document_id"] == document_id), None)

        if not doc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Document {document_id} not found",
            )

        # Delete from index
        num_deleted = indexer.delete_document(document_id)

        # Delete document file from filesystem
        doc_path = document_dir / doc["filename"]
        if doc_path.exists():
            doc_path.unlink()
            logger.info(f"Deleted document file: {doc['filename']}")

        # Persist the changes
        indexer.save_index()

        return {
            "message": f"Deleted document {document_id}",
            "filename": doc["filename"],
            "chunks_deleted": num_deleted,
            "file_deleted": True,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete document: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete document: {str(e)}",
        )


# Mount static files at root to serve /assets/* and other static content
# This must be last so it doesn't override API routes
app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="static")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=True,
    )
