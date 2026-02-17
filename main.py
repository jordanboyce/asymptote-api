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
from services.backup_service import BackupService
from services.index_repair import IndexRepairService
from models.schemas import (
    UploadResponse,
    SearchRequest,
    SearchResponse,
    DocumentListResponse,
    DocumentMetadata,
    AskRequest,
    AskResponse,
    AskSource,
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
    SUPPORTED_EXTENSIONS = {'.pdf', '.txt', '.docx', '.csv', '.md', '.json'}
    for file in files:
        file_ext = Path(file.filename).suffix.lower()
        if file_ext not in SUPPORTED_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File {file.filename} has unsupported type. Supported types: PDF, TXT, DOCX, CSV, MD, JSON",
            )

    indexed_docs = []
    failed_docs = []
    total_pages = 0
    total_chunks = 0

    for file in files:
        try:
            # Save uploaded file to collection's document directory
            # Use only the basename to avoid directory traversal issues
            safe_filename = Path(file.filename).name
            file_path = document_dir / safe_filename
            with open(file_path, "wb") as f:
                shutil.copyfileobj(file.file, f)

            logger.info(f"Saved uploaded file: {safe_filename} to collection {collection_id}")

            # Index the document
            doc_metadata = indexer.index_document(file_path, safe_filename)

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
                cleanup_path = document_dir / Path(file.filename).name
                if cleanup_path.exists():
                    cleanup_path.unlink()
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


@app.post(
    "/api/ask",
    response_model=AskResponse,
    summary="Ask a question about indexed documents",
    tags=["agent"],
)
async def ask_question(
    request: AskRequest,
    x_ai_key: str = Header(None),
    x_ai_provider: str = Header("anthropic"),
    x_ollama_model: str = Header(None),
):
    """
    Ask a question and get a synthesized answer from indexed documents.

    This endpoint is optimized for coding agents and AI assistants.

    **Processing Flow**:
    1. **Search**: Vector similarity search finds relevant document chunks
    2. **Rerank** (optional, default=true): AI reorders results by actual relevance
    3. **Synthesis**: AI generates coherent answer with citations
    4. **Response**: Clean, structured response returned to agent

    **API Key Options** (in order of precedence):
    1. Pass via X-AI-Key header (per-request)
    2. Use server-stored key (configured via /api/agent/config)
    3. For Ollama: no key needed, just set X-AI-Provider: ollama

    **Response Formats**:
    - `markdown`: Answer with markdown formatting and source citations
    - `text`: Plain text answer with inline citations
    - `json`: Structured JSON with answer and sources array

    **Token Usage**:
    - Rerank uses a fast model (lower cost) to judge relevance
    - Synthesis uses a quality model for answer generation
    - `tokens_used` in response is the total across both operations

    Example usage with curl:
    ```bash
    # Using header key
    curl -X POST http://localhost:8000/api/ask \\
      -H "Content-Type: application/json" \\
      -H "X-AI-Key: your-api-key" \\
      -d '{"question": "How do I configure the API?", "collection_id": "docs"}'

    # Using server-stored key (no header needed)
    curl -X POST http://localhost:8000/api/ask \\
      -H "Content-Type: application/json" \\
      -d '{"question": "How do I configure the API?"}'

    # Skip reranking for faster response (lower quality)
    curl -X POST http://localhost:8000/api/ask \\
      -H "Content-Type: application/json" \\
      -d '{"question": "How do I configure the API?", "rerank": false}'
    ```
    """
    from services.app_database import app_db
    import time
    start_time = time.time()

    # Validate AI provider is configured
    if x_ai_provider == "ollama":
        model = x_ollama_model or "llama3.2"
        try:
            provider = create_provider("ollama", model=model)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Ollama not available: {e}",
            )
    else:
        # Try header key first, then fall back to server-stored key
        api_key = x_ai_key or app_db.get_agent_api_key(x_ai_provider)
        if not api_key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"No API key configured for {x_ai_provider}. "
                       f"Either pass X-AI-Key header or configure via /api/agent/config.",
            )
        try:
            provider = create_provider(x_ai_provider, api_key)
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e),
            )

    # Get indexer for the collection
    try:
        indexer = get_indexer(request.collection_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )

    # Search for relevant chunks
    try:
        search_results = indexer.vector_store.search(
            indexer.embedding_service.embed_query(request.question),
            top_k=request.top_k,
        )
    except Exception as e:
        logger.error(f"Search failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Search failed: {e}",
        )

    if not search_results:
        return AskResponse(
            answer="No relevant documents found for your question.",
            sources=[],
            collection_id=request.collection_id,
            model=provider.QUALITY_MODEL,
            tokens_used=0,
        )

    # Track total token usage
    total_tokens = 0
    ai_service = AIService(provider=provider)

    # Rerank results if enabled (improves answer quality)
    if request.rerank:
        try:
            # Convert search results to format expected by rerank
            results_for_rerank = [
                {
                    "index": i,
                    "filename": r.filename,
                    "text_snippet": r.text_snippet,
                    "page_number": r.page_number,
                    "similarity_score": r.similarity_score,
                }
                for i, r in enumerate(search_results)
            ]

            rerank_result = ai_service.rerank_results(
                request.question, results_for_rerank, request.top_k
            )

            if rerank_result["usage"]:
                total_tokens += (
                    rerank_result["usage"]["input_tokens"] +
                    rerank_result["usage"]["output_tokens"]
                )

            # Reorder search results based on reranking
            reranked_indices = rerank_result["reranked_indices"]
            if reranked_indices:
                search_results = [
                    search_results[i]
                    for i in reranked_indices
                    if i < len(search_results)
                ]
                logger.info(f"Reranked to {len(search_results)} results")

        except Exception as e:
            logger.warning(f"Reranking failed, using original order: {e}")

    # Build context for AI synthesis
    context_parts = []
    sources = []
    for i, result in enumerate(search_results):
        # Truncate excerpt if needed
        excerpt = result.text_snippet
        if len(excerpt) > request.max_source_length:
            excerpt = excerpt[:request.max_source_length] + "..."

        context_parts.append(
            f"[Source {i + 1}: {result.filename}, page {result.page_number}]\n"
            f"{result.text_snippet}"
        )

        if request.include_sources:
            sources.append(AskSource(
                filename=result.filename,
                page=result.page_number,
                excerpt=excerpt,
                relevance=round(result.similarity_score, 3),
            ))

    context = "\n\n---\n\n".join(context_parts)

    # Build the synthesis prompt based on format
    if request.format == "json":
        format_instruction = (
            "Provide your answer as valid JSON with the structure: "
            '{"answer": "your answer here", "key_points": ["point 1", "point 2"]}'
        )
    elif request.format == "text":
        format_instruction = (
            "Provide your answer as plain text. Use inline citations like "
            "[Source 1] when referencing information."
        )
    else:  # markdown
        format_instruction = (
            "Format your answer using markdown. Use headers, lists, and code blocks "
            "as appropriate. Cite sources using [Source N] notation."
        )

    prompt = (
        "You are a knowledgeable assistant helping answer questions based on "
        "indexed documentation. Answer the question using ONLY the provided sources.\n\n"
        "Rules:\n"
        "- Only use information from the provided sources\n"
        "- Cite specific sources for each claim using [Source N]\n"
        "- If the sources don't contain enough information to fully answer, say so\n"
        "- Be concise but thorough\n"
        f"- {format_instruction}\n\n"
        f"Question: {request.question}\n\n"
        f"Sources:\n{context}"
    )

    # Generate answer
    try:
        response = provider.complete(prompt, max_tokens=1500, model=provider.QUALITY_MODEL)
        answer = response["text"]
        total_tokens += response["usage"]["input_tokens"] + response["usage"]["output_tokens"]
        model_used = response["usage"]["model"]
    except Exception as e:
        logger.error(f"AI synthesis failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"AI synthesis failed: {e}",
        )

    elapsed = time.time() - start_time
    logger.info(f"Ask query completed in {elapsed:.2f}s using {model_used}")

    return AskResponse(
        answer=answer,
        sources=sources,
        collection_id=request.collection_id,
        model=model_used,
        tokens_used=total_tokens,
    )


@app.get(
    "/api/agent/config",
    summary="Get agent API configuration",
    tags=["agent"],
)
async def get_agent_config():
    """
    Get the current agent API configuration.

    Returns which providers have API keys configured (keys are masked for security).
    """
    from services.app_database import app_db
    return app_db.get_agent_config()


@app.post(
    "/api/agent/config",
    summary="Configure agent API key",
    tags=["agent"],
)
async def set_agent_config(
    provider: str,
    api_key: str,
):
    """
    Store an API key for agent use.

    This allows the /api/ask endpoint to work without requiring
    the X-AI-Key header on every request.

    Args:
        provider: AI provider name (anthropic, openai)
        api_key: The API key to store

    Note: Keys are stored server-side. For security, ensure your
    Asymptote instance is properly secured.
    """
    from services.app_database import app_db

    if provider not in ("anthropic", "openai"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid provider: {provider}. Use 'anthropic' or 'openai'.",
        )

    # Validate the key before storing
    try:
        test_provider = create_provider(provider, api_key)
        valid = test_provider.validate()
        if not valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"API key validation failed for {provider}",
            )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"API key validation failed: {e}",
        )

    app_db.set_agent_api_key(provider, api_key)
    return {"success": True, "message": f"API key configured for {provider}"}


@app.delete(
    "/api/agent/config/{provider}",
    summary="Remove agent API key",
    tags=["agent"],
)
async def delete_agent_config(provider: str):
    """
    Remove a stored API key.

    Args:
        provider: AI provider name (anthropic, openai)
    """
    from services.app_database import app_db

    if provider not in ("anthropic", "openai"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid provider: {provider}",
        )

    app_db.delete_agent_api_key(provider)
    return {"success": True, "message": f"API key removed for {provider}"}


@app.get(
    "/api/agent/collections",
    summary="List collections available to agents",
    tags=["agent"],
)
async def list_agent_collections():
    """
    List all collections available for agent queries.

    Returns collection IDs, names, and document counts.
    Useful for agents to discover what collections are available.
    """
    collections = collection_service.get_all_collections()
    result = []

    for c in collections:
        collection_id = c["id"]
        # Get actual document/chunk counts from the indexer
        stats = indexer_manager.get_collection_stats(collection_id)

        result.append({
            "id": collection_id,
            "name": c["name"],
            "description": c.get("description", ""),
            "document_count": stats.get("total_documents", 0),
            "chunk_count": stats.get("total_chunks", 0),
        })

    return {"collections": result}


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

    try:
        # Remove cached indexer first (before files are deleted)
        indexer_manager.remove_indexer(collection_id)

        success = collection_service.delete_collection(collection_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Collection '{collection_id}' not found"
            )

        return {"message": f"Collection '{collection_id}' deleted", "success": True}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete collection '{collection_id}': {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete collection: {str(e)}"
        )


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


# Backup/Restore endpoints (v3.0 feature)
backup_service = BackupService()


@app.get(
    "/api/backups",
    summary="List all backups",
    tags=["backup"],
)
async def list_backups():
    """
    List all available backup files.

    Returns list of backups with metadata including:
    - filename, size, creation time
    - collection_id, description
    - whether documents are included
    - storage type and embedding model used
    """
    backups = backup_service.list_backups()
    return {"backups": backups}


@app.post(
    "/api/backups",
    summary="Create a backup",
    tags=["backup"],
    status_code=status.HTTP_201_CREATED,
)
async def create_backup(
    collection_id: str = "default",
    description: str = "",
    include_documents: bool = True,
):
    """
    Create a backup of a collection's index and documents.

    Args:
        collection_id: Collection to backup (default: "default")
        description: Optional description for the backup
        include_documents: Whether to include source document files (default: True)

    Returns:
        Backup file information including path and size
    """
    try:
        backup_path = backup_service.create_backup(
            collection_id=collection_id,
            description=description,
            include_documents=include_documents,
        )

        return {
            "success": True,
            "filename": backup_path.name,
            "path": str(backup_path),
            "size_mb": backup_path.stat().st_size / 1024 / 1024,
            "collection_id": collection_id,
            "includes_documents": include_documents,
        }
    except Exception as e:
        logger.error(f"Backup creation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Backup creation failed: {str(e)}",
        )


@app.get(
    "/api/backups/{backup_filename}",
    summary="Get backup details",
    tags=["backup"],
)
async def get_backup_info(backup_filename: str):
    """
    Get detailed information about a specific backup.

    Args:
        backup_filename: Name of the backup file

    Returns full backup metadata and file listing.
    """
    info = backup_service.get_backup_info(backup_filename)
    if not info:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Backup '{backup_filename}' not found",
        )
    return info


@app.post(
    "/api/backups/{backup_filename}/restore",
    summary="Restore from backup",
    tags=["backup"],
)
async def restore_backup(
    backup_filename: str,
    target_collection_id: str = None,
    overwrite: bool = False,
):
    """
    Restore a collection from a backup file.

    Args:
        backup_filename: Name of the backup file to restore
        target_collection_id: Collection ID to restore to (default: use original)
        overwrite: Whether to overwrite existing data (default: False)

    Returns restore results including files restored.
    """
    import gc

    backup_path = backup_service.backup_dir / backup_filename

    # Determine collection ID from backup metadata first
    backup_info = backup_service.get_backup_info(backup_filename)
    if not backup_info:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Backup file '{backup_filename}' not found",
        )

    collection_id = target_collection_id or backup_info.get("collection_id", "default")

    # Close the indexer to release database file handles before restore
    # This is critical on Windows where files can't be deleted while open
    if overwrite:
        logger.info(f"Closing indexer for '{collection_id}' before restore...")
        indexer_manager.close_indexer(collection_id)
        # Force garbage collection to release file handles
        gc.collect()

    try:
        result = backup_service.restore_backup(
            backup_path=backup_path,
            target_collection_id=target_collection_id,
            overwrite=overwrite,
        )

        # Load/reload the indexer for the restored collection
        collection_id = result["collection_id"]
        try:
            # First invalidate any existing cached indexer
            indexer_manager.remove_indexer(collection_id)
            # Then load the indexer fresh from the restored data
            indexer = indexer_manager.get_indexer(collection_id)
            logger.info(f"Loaded indexer for restored collection '{collection_id}' with {indexer.vector_store.get_total_chunks()} chunks")
        except Exception as e:
            logger.warning(f"Could not load indexer after restore: {e}")

        return result
    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Backup file '{backup_filename}' not found",
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Restore failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Restore failed: {str(e)}",
        )


@app.delete(
    "/api/backups/{backup_filename}",
    summary="Delete a backup",
    tags=["backup"],
)
async def delete_backup(backup_filename: str):
    """
    Delete a backup file.

    Args:
        backup_filename: Name of the backup file to delete
    """
    if not backup_service.delete_backup(backup_filename):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Backup '{backup_filename}' not found",
        )

    return {"success": True, "message": f"Backup '{backup_filename}' deleted"}


@app.get(
    "/api/index/diagnose",
    summary="Diagnose index sync status",
    tags=["admin"],
)
async def diagnose_index(collection_id: str = "default"):
    """
    Diagnose synchronization between FAISS index and metadata.

    Args:
        collection_id: Collection to diagnose (default: "default")

    Returns:
        Diagnostic information including:
        - faiss_count: Number of vectors in FAISS
        - metadata_count: Number of chunks in metadata
        - embeddings_count: Number of stored embeddings
        - status: synced, out_of_sync, missing_index, etc.
        - issues: List of detected problems
        - recommendations: Suggested fixes
    """
    try:
        indexes_path = indexer_manager.get_indexes_path(collection_id)
        repair_service = IndexRepairService(indexes_path)
        return repair_service.diagnose()
    except Exception as e:
        logger.error(f"Index diagnosis failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Diagnosis failed: {str(e)}",
        )


@app.post(
    "/api/index/repair",
    summary="Repair index synchronization",
    tags=["admin"],
)
async def repair_index(
    collection_id: str = "default",
    method: str = "rebuild",
):
    """
    Repair FAISS-metadata synchronization issues.

    Args:
        collection_id: Collection to repair (default: "default")
        method: Repair method:
            - "rebuild": Re-embed all text from metadata (safest, slowest)
            - "truncate": Remove orphaned FAISS entries
            - "repair_documents": Reconstruct missing document records from chunks

    The "rebuild" method is safer but slower - it re-embeds all text from metadata.
    The "truncate" method is faster but only works if FAISS has more entries than metadata.
    The "repair_documents" method fixes cases where chunks exist but document records are missing.

    Returns:
        Repair results including success status and details.
    """
    try:
        indexes_path = indexer_manager.get_indexes_path(collection_id)

        if method == "rebuild":
            # Need embedding service for rebuilding
            indexer = get_indexer(collection_id)
            repair_service = IndexRepairService(
                indexes_path,
                embedding_service=indexer.embedding_service
            )
            result = repair_service.rebuild_from_metadata(
                embedding_dim=indexer.embedding_service.embedding_dim
            )
        elif method == "truncate":
            repair_service = IndexRepairService(indexes_path)
            result = repair_service.truncate_faiss_to_metadata()
        elif method == "repair_documents":
            repair_service = IndexRepairService(indexes_path)
            result = repair_service.repair_documents_table()
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unknown repair method: {method}. Use 'rebuild', 'truncate', or 'repair_documents'.",
            )

        if result.get("success"):
            # Reload the indexer to pick up the repaired index
            indexer_manager.reload_indexer(collection_id)

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Index repair failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Repair failed: {str(e)}",
        )


@app.get(
    "/api/backups/{backup_filename}/download",
    summary="Download a backup file",
    tags=["backup"],
    response_class=FileResponse,
)
async def download_backup(backup_filename: str):
    """
    Download a backup file.

    Args:
        backup_filename: Name of the backup file to download
    """
    backup_path = backup_service.backup_dir / backup_filename

    if not backup_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Backup '{backup_filename}' not found",
        )

    return FileResponse(
        path=backup_path,
        media_type="application/zip",
        filename=backup_filename,
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
