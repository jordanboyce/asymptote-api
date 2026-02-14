"""
Asymptote API - Self-hosted semantic search for documents

Main application entry point.
Supports PDF, TXT, DOCX, and CSV files.
"""

import logging
import json
from contextlib import asynccontextmanager
from typing import List
from pathlib import Path
import shutil

from fastapi import FastAPI, Depends, Header, HTTPException, UploadFile, File, status, Request
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
from services.ai_service import AIService, create_provider, detect_ollama
from services.config_manager import config_manager
from services.reindex_service import reindex_service
from services.collection_service import collection_service
from services.indexer_manager import indexer_manager
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


# Global services flag
_initialized = False


def get_indexer(collection_id: str = "default") -> DocumentIndexer:
    """Get indexer for a collection."""
    if not _initialized:
        raise HTTPException(
            status_code=503,
            detail="Service is still initializing. Please wait a moment and try again."
        )
    return indexer_manager.get_indexer(collection_id)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager - initialize and cleanup services."""
    global _initialized

    logger.info("Initializing Asymptote API...")

    # Initialize default collection's indexer to pre-load embedding model
    logger.info("Loading default collection indexer...")
    try:
        default_indexer = indexer_manager.get_indexer("default")
        total_chunks = default_indexer.vector_store.get_total_chunks()
        logger.info(f"Default collection indexed chunks: {total_chunks}")
    except Exception as e:
        logger.warning(f"Could not load default indexer: {e}")

    # Set up reload callback for re-indexing service (collection-aware)
    def reload_indexer(collection_id: str = "default"):
        """Reload an indexer's vector store from disk after re-indexing."""
        try:
            logger.info("=" * 60)
            logger.info(f"RELOAD CALLBACK TRIGGERED for collection: {collection_id}")
            logger.info("=" * 60)

            indexer_manager.reload_indexer(collection_id)

            stats = indexer_manager.get_collection_stats(collection_id)
            logger.info(f"Reload complete. Collection {collection_id} indexed chunks: {stats['total_chunks']}")
            logger.info("=" * 60)

        except Exception as e:
            logger.error(f"RELOAD FAILED for collection {collection_id}: {e}", exc_info=True)

    reindex_service.reload_callback = reload_indexer

    _initialized = True

    logger.info("Asymptote API ready")
    logger.info(f"Data directory: {settings.data_dir}")
    logger.info(f"Metadata storage: {settings.metadata_storage}")

    yield

    # Cleanup on shutdown
    logger.info("Shutting down Asymptote API...")
    indexer_manager.save_all()
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
async def health(collection_id: str = "default"):
    """Health check endpoint."""
    try:
        stats = indexer_manager.get_collection_stats(collection_id)
        return {
            "status": "healthy",
            "collection_id": collection_id,
            "indexed_chunks": stats["total_chunks"],
            "total_documents": stats["total_documents"],
            "total_pages": stats["total_pages"],
        }
    except Exception as e:
        return {
            "status": "healthy",
            "indexed_chunks": 0,
            "error": str(e),
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
    collection_id: str = "default",
) -> UploadResponse:
    """
    Upload one or more documents and automatically index their contents.

    Supported formats: PDF, TXT, DOCX, CSV

    Args:
        files: List of files to upload
        collection_id: Collection to add documents to (default: "default")

    Returns metadata about the indexed documents including page and chunk counts.
    """
    if not files:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No files provided",
        )

    # Get indexer for the collection
    try:
        indexer = get_indexer(collection_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )

    # Get document directory for this collection
    document_dir = indexer_manager.get_documents_path(collection_id)

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
    failed_docs = []
    total_pages = 0
    total_chunks = 0

    for file in files:
        try:
            # Save uploaded file to collection's document directory
            file_path = document_dir / file.filename
            with open(file_path, "wb") as f:
                shutil.copyfileobj(file.file, f)

            logger.info(f"Saved uploaded file: {file.filename} to collection {collection_id}")

            # Index the document
            doc_metadata = indexer.index_document(file_path, file.filename)

            # Register document with collection
            collection_service.add_document(collection_id, doc_metadata.document_id)

            indexed_docs.append(doc_metadata.document_id)
            total_pages += doc_metadata.total_pages
            total_chunks += doc_metadata.total_chunks

        except Exception as e:
            logger.error(f"Failed to index {file.filename}: {e}")
            failed_docs.append({"filename": file.filename, "error": str(e)})
            # Clean up the saved file if indexing failed
            try:
                file_path = document_dir / file.filename
                if file_path.exists():
                    file_path.unlink()
            except Exception:
                pass
            # Continue processing remaining files

    # Persist the index if any documents were successfully indexed
    if indexed_docs:
        indexer.save_index()

    # Build response message
    if failed_docs and not indexed_docs:
        # All files failed
        error_details = "; ".join([f"{f['filename']}: {f['error']}" for f in failed_docs])
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"All files failed to index. Errors: {error_details}",
        )

    if failed_docs:
        # Partial success
        failed_names = [f["filename"] for f in failed_docs]
        message = f"Indexed {len(indexed_docs)} document(s) to collection '{collection_id}'. Failed: {', '.join(failed_names)}"
    else:
        # Full success
        message = f"Successfully indexed {len(indexed_docs)} document(s) to collection '{collection_id}'"

    return UploadResponse(
        message=message,
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
    collection_id: str = "default",
    x_ai_key: str = Header(None),
    x_ollama_model: str = Header(None),
) -> SearchResponse:
    """
    Perform semantic similarity search over indexed documents.

    Args:
        search_request: Search query and options
        collection_id: Collection to search (default: "default")

    Optionally enable AI enhancements by including 'ai' options in the request body.
    Supports Anthropic, OpenAI, and Ollama providers.

    For cloud providers (Anthropic, OpenAI):
    - Pass API key via X-AI-Key header
    - Set provider in request body ai.provider

    For Ollama:
    - Pass model name via X-Ollama-Model header (e.g., llama3.2)
    - Set provider to 'ollama' in request body ai.provider
    - No API key required
    """
    try:
        import time
        start_time = time.time()

        # Get indexer for the collection
        try:
            indexer = get_indexer(collection_id)
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(e),
            )

        # Build AI service if AI options requested
        ai_service = None
        ai_options = search_request.ai
        ai_provider_used = None

        if ai_options:
            try:
                if ai_options.provider == "ollama":
                    # Ollama doesn't need API key
                    model = x_ollama_model or "llama3.2"
                    provider = create_provider("ollama", model=model)
                    ai_service = AIService(provider=provider)
                    ai_provider_used = "ollama"
                else:
                    # Cloud providers need API key
                    if not x_ai_key:
                        logger.warning(f"AI key required for provider: {ai_options.provider}")
                    else:
                        provider = create_provider(ai_options.provider, x_ai_key)
                        ai_service = AIService(provider=provider)
                        ai_provider_used = ai_options.provider
            except Exception as e:
                logger.warning(f"Failed to create AI service: {e}")

        search_result = indexer.search(
            query=search_request.query,
            top_k=search_request.top_k,
            ai_service=ai_service,
            ai_options=ai_options,
        )

        results = search_result["results"]

        # Add URLs to each result (include collection_id for proper routing)
        base_url = str(request.base_url).rstrip('/')
        for result in results:
            result.pdf_url = f"{base_url}/documents/{result.document_id}/pdf?collection_id={collection_id}"
            result.page_url = f"{base_url}/documents/{result.document_id}/pdf?collection_id={collection_id}#page={result.page_number}"

        execution_time_ms = int((time.time() - start_time) * 1000)

        # Save to search history
        from services.app_database import app_db
        try:
            results_json = json.dumps([{
                "document_id": r.document_id,
                "filename": r.filename,
                "page_number": r.page_number,
                "chunk_index": r.chunk_index,
                "text": r.text,
                "similarity": r.similarity,
                "pdf_url": r.pdf_url,
                "page_url": r.page_url
            } for r in results])

            app_db.add_search_history(
                query=search_request.query,
                top_k=search_request.top_k,
                results_count=len(results),
                ai_provider=ai_provider_used,
                ai_used=ai_service is not None,
                results_json=results_json,
                execution_time_ms=execution_time_ms
            )
        except Exception as e:
            logger.warning(f"Failed to save search history: {e}")

        return SearchResponse(
            query=search_request.query,
            results=results,
            total_results=len(results),
            synthesis=search_result.get("synthesis"),
            ai_usage=search_result.get("ai_usage"),
        )

    except Exception as e:
        logger.error(f"Search failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Search failed: {str(e)}",
        )


@app.post(
    "/api/ai/validate-key",
    summary="Validate an AI provider API key or Ollama model",
    tags=["ai"],
)
async def validate_api_key(
    x_ai_key: str = Header(None),
    x_ai_provider: str = Header("anthropic"),
    x_ollama_model: str = Header(None),
):
    """
    Validate an API key or Ollama model availability.

    For cloud providers (Anthropic, OpenAI):
    - Pass the key via X-AI-Key header
    - Pass provider via X-AI-Provider header

    For Ollama:
    - Pass 'ollama' via X-AI-Provider header
    - Pass model name via X-Ollama-Model header
    - X-AI-Key is not required
    """
    try:
        if x_ai_provider == "ollama":
            # Ollama doesn't need API key
            model = x_ollama_model or "llama3.2"
            provider = create_provider("ollama", model=model)
        else:
            # Cloud providers need API key
            if not x_ai_key:
                return {"valid": False, "error": "API key is required for cloud providers"}
            provider = create_provider(x_ai_provider, x_ai_key)

        valid = provider.validate()
        return {"valid": valid, "error": None}
    except Exception as e:
        error_str = str(e)
        logger.error(f"API key validation error for {x_ai_provider}: {e}")

        # Provide more helpful error messages
        if "quota" in error_str.lower() or "insufficient_quota" in error_str.lower():
            return {"valid": False, "error": "Your API key has exceeded its quota. Please add credits to your account."}
        elif "rate" in error_str.lower() and "limit" in error_str.lower():
            return {"valid": False, "error": "Rate limit exceeded. Please wait a moment and try again."}
        else:
            return {"valid": False, "error": error_str}


@app.get(
    "/api/config",
    summary="Get current configuration",
    tags=["config"],
)
async def get_config():
    """
    Get current configuration settings.

    Returns all configurable settings including embedding model,
    chunking parameters, and storage type.
    """
    return config_manager.get_current_config()


@app.post(
    "/api/config",
    summary="Update configuration",
    tags=["config"],
)
async def update_config(updates: dict):
    """
    Update configuration settings.

    Args:
        updates: Dictionary of configuration key-value pairs

    Returns:
        Object with success status, whether restart/reindex needed,
        and list of updated fields.

    Note: Some changes (like embedding model) require server restart
    and re-indexing all documents.
    """
    result = config_manager.update_config(updates)
    return result


@app.get(
    "/api/config/embedding-models",
    summary="List available embedding models",
    tags=["config"],
)
async def list_embedding_models():
    """
    Get list of recommended embedding models with their properties.

    Returns list of models with details like dimensions, size,
    speed, and quality ratings.
    """
    return {"models": config_manager.get_embedding_models()}


@app.get(
    "/api/ollama/status",
    summary="Check Ollama availability",
    tags=["ai"],
)
async def get_ollama_status():
    """
    Check if Ollama is running and list available models.

    Returns:
        - available: Whether Ollama is accessible
        - models: List of available models with names and sizes
        - error: Error message if detection failed
    """
    return detect_ollama()


@app.post(
    "/api/ollama/validate",
    summary="Validate Ollama model availability",
    tags=["ai"],
)
async def validate_ollama_model(model_name: str):
    """
    Check if a specific Ollama model is available.

    Args:
        model_name: Name of the Ollama model to check

    Returns:
        - valid: Whether the model is available
        - error: Error message if not available
    """
    try:
        provider = create_provider("ollama", model=model_name)
        valid = provider.validate()
        return {"valid": valid, "error": None if valid else f"Model '{model_name}' not found"}
    except Exception as e:
        return {"valid": False, "error": str(e)}


@app.post(
    "/api/reindex",
    summary="Start re-indexing all documents",
    tags=["admin"],
)
async def start_reindex():
    """
    Start a background re-indexing job for all documents.

    Uses current configuration from database or settings.
    Returns immediately with job ID for progress tracking.

    Returns:
        - job_id: ID for tracking re-indexing progress
        - status: Initial job status
    """
    try:
        # Get current config (from database with .env fallback)
        current_config = config_manager.get_current_config()

        # Get embedding dimensions
        embedding_service = EmbeddingService(model_name=current_config["embedding_model"])
        embedding_dim = embedding_service.embedding_dim

        # Start re-indexing
        job_id = await reindex_service.start_reindex(
            documents_dir=settings.data_dir / "documents",
            embedding_model=current_config["embedding_model"],
            chunk_size=current_config["chunk_size"],
            chunk_overlap=current_config["chunk_overlap"],
            metadata_storage=current_config["metadata_storage"],
            embedding_dim=embedding_dim,
        )

        return {
            "job_id": job_id,
            "status": "started",
            "message": "Re-indexing job started in background"
        }

    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to start re-indexing: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start re-indexing: {str(e)}"
        )


@app.post(
    "/api/collections/{collection_id}/reindex",
    summary="Start re-indexing a collection",
    tags=["collections"],
)
async def start_collection_reindex(collection_id: str):
    """
    Start a background re-indexing job for a specific collection.

    Re-indexes all documents in the collection using the collection's
    current settings (chunk_size, chunk_overlap, embedding_model).

    This is useful after changing collection settings to apply
    the new settings to existing documents.

    Args:
        collection_id: Collection to reindex

    Returns:
        - job_id: ID for tracking re-indexing progress
        - status: Initial job status
        - collection_id: Collection being reindexed
    """
    try:
        # Get collection settings
        collection = collection_service.get_collection(collection_id)
        if not collection:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Collection '{collection_id}' not found"
            )

        # Get collection paths
        documents_dir = indexer_manager.get_documents_path(collection_id)
        indexes_dir = indexer_manager.get_indexes_path(collection_id)

        # Get embedding dimensions for the collection's model
        embedding_service = EmbeddingService(model_name=collection["embedding_model"])
        embedding_dim = embedding_service.embedding_dim

        # Start re-indexing
        job_id = await reindex_service.start_collection_reindex(
            collection_id=collection_id,
            documents_dir=documents_dir,
            indexes_dir=indexes_dir,
            embedding_model=collection["embedding_model"],
            chunk_size=collection["chunk_size"],
            chunk_overlap=collection["chunk_overlap"],
            metadata_storage=settings.metadata_storage,
            embedding_dim=embedding_dim,
        )

        return {
            "job_id": job_id,
            "status": "started",
            "collection_id": collection_id,
            "message": f"Re-indexing job started for collection '{collection_id}'"
        }

    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to start re-indexing for collection {collection_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start re-indexing: {str(e)}"
        )


@app.get(
    "/api/reindex/status",
    summary="Get re-indexing job status",
    tags=["admin"],
)
async def get_reindex_status(job_id: int = None):
    """
    Get status of a re-indexing job.

    Args:
        job_id: Optional job ID. If not provided, returns latest job.

    Returns:
        Job details including:
        - id: Job ID
        - status: pending, running, completed, or failed
        - total_documents: Total documents to process
        - processed_documents: Documents processed so far
        - current_file: Currently processing file
        - started_at: Job start timestamp
        - completed_at: Job completion timestamp (if finished)
        - error: Error message (if failed)
    """
    from services.app_database import app_db

    if job_id:
        job = reindex_service.get_job_status(job_id)
    else:
        # Get latest job (including completed ones), not just currently active
        job = app_db.get_latest_reindex_job()

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No re-indexing job found"
        )

    # Calculate progress percentage
    if job["total_documents"] > 0:
        progress = (job["processed_documents"] / job["total_documents"]) * 100
    else:
        progress = 0

    return {
        **job,
        "progress_percent": round(progress, 1)
    }


# AI Preferences endpoints
@app.get(
    "/api/ai/preferences",
    summary="Get AI preferences",
    tags=["ai"],
)
async def get_ai_preferences():
    """Get AI provider preferences."""
    from services.app_database import app_db
    prefs = app_db.get_ai_preferences()
    if not prefs:
        # Return defaults
        return {
            "selected_providers": [],
            "rerank_enabled": True,
            "synthesize_enabled": True,
            "default_provider": None
        }
    return prefs


@app.post(
    "/api/ai/preferences",
    summary="Set AI preferences",
    tags=["ai"],
)
async def set_ai_preferences(preferences: dict):
    """
    Set AI provider preferences.

    Body:
        selected_providers: List of provider names
        rerank_enabled: Boolean
        synthesize_enabled: Boolean
        default_provider: Provider name
    """
    from services.app_database import app_db
    app_db.set_ai_preferences(
        selected_providers=preferences.get("selected_providers"),
        rerank_enabled=preferences.get("rerank_enabled"),
        synthesize_enabled=preferences.get("synthesize_enabled"),
        default_provider=preferences.get("default_provider")
    )
    return {"success": True}


# Search History endpoints
@app.get(
    "/api/search/history",
    summary="Get search history",
    tags=["search"],
)
async def get_search_history(limit: int = 50):
    """Get recent search history."""
    from services.app_database import app_db
    return {"history": app_db.get_search_history(limit=limit)}


@app.get(
    "/api/search/history/{search_id}",
    summary="Get cached search results",
    tags=["search"],
)
async def get_cached_search(search_id: int):
    """Get cached search results by ID."""
    from services.app_database import app_db
    search = app_db.get_search_by_id(search_id)
    if not search:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Search not found"
        )
    return search


@app.delete(
    "/api/search/history",
    summary="Clear old search history",
    tags=["search"],
)
async def clear_old_history(days: int = 30):
    """Delete search history older than specified days."""
    from services.app_database import app_db
    deleted = app_db.delete_old_search_history(days=days)
    return {"deleted": deleted, "message": f"Deleted {deleted} old searches"}


# User Preferences endpoints
@app.get(
    "/api/preferences",
    summary="Get all user preferences",
    tags=["preferences"],
)
async def get_preferences():
    """Get all user preferences."""
    from services.app_database import app_db
    return app_db.get_all_user_preferences()


@app.get(
    "/api/preferences/{key}",
    summary="Get user preference",
    tags=["preferences"],
)
async def get_preference(key: str, default: str = None):
    """Get specific user preference."""
    from services.app_database import app_db
    value = app_db.get_user_preference(key, default)
    return {"key": key, "value": value}


@app.post(
    "/api/preferences",
    summary="Set user preference",
    tags=["preferences"],
)
async def set_preference(preference: dict):
    """
    Set user preference.

    Body:
        key: Preference key
        value: Preference value
    """
    from services.app_database import app_db
    key = preference.get("key")
    value = preference.get("value")

    if not key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Key is required"
        )

    app_db.set_user_preference(key, value)
    return {"success": True, "key": key}


# Collection endpoints
@app.get(
    "/api/collections",
    summary="List all collections",
    tags=["collections"],
)
async def list_collections():
    """Get all document collections."""
    collections = collection_service.get_all_collections()
    return {"collections": collections}


@app.post(
    "/api/collections",
    summary="Create a new collection",
    tags=["collections"],
    status_code=status.HTTP_201_CREATED,
)
async def create_collection(collection_data: dict):
    """
    Create a new document collection.

    Body:
        name: Collection name (required)
        description: Collection description
        color: Hex color for UI (default: #3b82f6)
        chunk_size: Text chunk size (default: 500)
        chunk_overlap: Chunk overlap (default: 50)
        embedding_model: Embedding model to use
    """
    name = collection_data.get("name")
    if not name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Collection name is required"
        )

    collection = collection_service.create_collection(
        name=name,
        description=collection_data.get("description", ""),
        color=collection_data.get("color", "#3b82f6"),
        chunk_size=collection_data.get("chunk_size", 500),
        chunk_overlap=collection_data.get("chunk_overlap", 50),
        embedding_model=collection_data.get("embedding_model", "all-MiniLM-L6-v2")
    )

    return collection


@app.get(
    "/api/collections/{collection_id}",
    summary="Get collection details",
    tags=["collections"],
)
async def get_collection(collection_id: str):
    """Get details for a specific collection."""
    collection = collection_service.get_collection(collection_id)
    if not collection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Collection '{collection_id}' not found"
        )
    return collection


@app.put(
    "/api/collections/{collection_id}",
    summary="Update collection settings",
    tags=["collections"],
)
async def update_collection(collection_id: str, updates: dict):
    """
    Update collection settings.

    Body:
        name: New name
        description: New description
        color: New hex color
        chunk_size: New chunk size
        chunk_overlap: New chunk overlap
        embedding_model: New embedding model

    Note: Changing chunk_size, chunk_overlap, or embedding_model
    requires re-indexing the collection's documents.
    """
    collection = collection_service.update_collection(
        collection_id=collection_id,
        name=updates.get("name"),
        description=updates.get("description"),
        color=updates.get("color"),
        chunk_size=updates.get("chunk_size"),
        chunk_overlap=updates.get("chunk_overlap"),
        embedding_model=updates.get("embedding_model")
    )

    if not collection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Collection '{collection_id}' not found"
        )

    return collection


@app.delete(
    "/api/collections/{collection_id}",
    summary="Delete a collection",
    tags=["collections"],
)
async def delete_collection(collection_id: str):
    """
    Delete a collection and all its documents.

    Note: The 'default' collection cannot be deleted.
    """
    if collection_id == "default":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete the default collection"
        )

    success = collection_service.delete_collection(collection_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Collection '{collection_id}' not found"
        )

    return {"message": f"Collection '{collection_id}' deleted", "success": True}


@app.get(
    "/documents",
    response_model=DocumentListResponse,
    summary="List all indexed documents",
    tags=["documents"],
)
async def list_documents(
    collection_id: str = "default",
) -> DocumentListResponse:
    """
    List all indexed documents with their metadata.

    Args:
        collection_id: Collection to list documents from (default: "default")

    Returns filename, page count, and chunk count for each document.
    """
    try:
        # Get indexer for the collection
        try:
            indexer = get_indexer(collection_id)
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(e),
            )

        # Get document directory for this collection
        document_dir = indexer_manager.get_documents_path(collection_id)

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

            # Handle both field naming conventions (total_pages/num_pages, total_chunks/num_chunks)
            total_pages = doc.get("total_pages") or doc.get("num_pages", 0)
            total_chunks = doc.get("total_chunks") or doc.get("num_chunks", 0)

            doc_metadata = DocumentMetadata(
                document_id=doc["document_id"],
                filename=doc["filename"],
                total_pages=total_pages,
                total_chunks=total_chunks,
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
    collection_id: str = "default",
):
    """
    Download the document file for a specific document.

    Args:
        document_id: Document ID
        collection_id: Collection containing the document (default: "default")

    For PDFs, the URL can include #page=N to open at a specific page in the browser.
    """
    try:
        # Get indexer for the collection
        try:
            indexer = get_indexer(collection_id)
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(e),
            )

        # Get document directory for this collection
        document_dir = indexer_manager.get_documents_path(collection_id)

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
    collection_id: str = "default",
):
    """
    Remove a document and all its chunks from the index.

    Args:
        document_id: Document ID to delete
        collection_id: Collection containing the document (default: "default")

    This will delete:
    - The document's metadata from the index
    - All chunks associated with the document
    - The document file from the collection's documents directory
    """
    try:
        # Get indexer for the collection
        try:
            indexer = get_indexer(collection_id)
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(e),
            )

        # Get document directory for this collection
        document_dir = indexer_manager.get_documents_path(collection_id)

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

        # Remove document from collection tracking
        collection_service.remove_document(collection_id, document_id)

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
