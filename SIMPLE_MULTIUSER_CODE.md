# Simple Multi-User Implementation Code

**Exact code to add for browser-based multi-user support.**

---

## 1. Frontend: Add User ID to All Requests

Add this to `frontend/src/App.vue` in the `<script setup>` section:

```javascript
// Generate or retrieve user ID from localStorage
const initUserTracking = () => {
  let userId = localStorage.getItem('asymptote_user_id')

  if (!userId) {
    // Generate random user ID
    userId = 'user_' +
             Math.random().toString(36).substring(2, 15) +
             Math.random().toString(36).substring(2, 15)
    localStorage.setItem('asymptote_user_id', userId)
    console.log('👤 New user ID:', userId)
  } else {
    console.log('👤 Existing user ID:', userId)
  }

  // Add user ID to all axios requests
  axios.interceptors.request.use((config) => {
    config.headers['X-User-ID'] = userId
    return config
  })
}

// Call on component mount
onMounted(() => {
  initUserTracking()
  loadStats()
  // ... rest of your onMounted code
})
```

**That's it for frontend!** Every API request now includes `X-User-ID` header.

---

## 2. Backend: Handle User-Specific Storage

Add these functions to `main.py` after the imports:

```python
from typing import Optional
from fastapi import Header

def get_user_id_from_header(x_user_id: Optional[str] = Header(None)) -> Optional[str]:
    """
    Extract user ID from X-User-ID header if multi-user mode is enabled.

    Returns:
        Sanitized user ID or None
    """
    if not settings.enable_multi_user or not x_user_id:
        return None

    # Sanitize user ID for filesystem safety
    safe_user_id = "".join(c for c in x_user_id if c.isalnum() or c in "-_")
    return safe_user_id


def get_user_storage_paths(user_id: Optional[str]) -> tuple[Path, Path]:
    """
    Get user-specific or shared storage paths.

    Args:
        user_id: User identifier from header

    Returns:
        Tuple of (documents_directory, indexes_directory)
    """
    if user_id:
        # Multi-user mode: per-user directories
        user_base = settings.data_dir / "users" / user_id
        user_base.mkdir(parents=True, exist_ok=True)

        docs_dir = user_base / "documents"
        docs_dir.mkdir(parents=True, exist_ok=True)

        indexes_dir = user_base / "indexes"
        indexes_dir.mkdir(parents=True, exist_ok=True)

        logger.debug(f"Using user-specific storage for: {user_id}")
        return docs_dir, indexes_dir
    else:
        # Single-user mode: shared directories (default)
        return document_dir, settings.data_dir / "indexes"


def get_user_indexer(user_id: Optional[str]) -> DocumentIndexer:
    """
    Get user-specific or shared indexer.

    Args:
        user_id: User identifier

    Returns:
        DocumentIndexer instance
    """
    if not user_id:
        # Return shared indexer
        if _indexer is None:
            raise HTTPException(status_code=503, detail="Service initializing")
        return _indexer

    # Create user-specific indexer
    _, indexes_dir = get_user_storage_paths(user_id)

    if settings.metadata_storage.lower() == "sqlite":
        vector_store = VectorStoreV2(
            index_dir=indexes_dir,
            embedding_dim=_embedding_service.embedding_dim,
        )
    else:
        vector_store = VectorStore(
            index_dir=indexes_dir,
            embedding_dim=_embedding_service.embedding_dim,
        )

    return DocumentIndexer(
        vector_store=vector_store,
        embedding_service=_embedding_service,
        document_extractor=_document_extractor,
        text_chunker=_text_chunker,
    )
```

---

## 3. Update Startup Code

Replace the `lifespan` function in `main.py`:

```python
# Add these globals at the top with _indexer
_embedding_service: EmbeddingService = None
_document_extractor: DocumentExtractor = None
_text_chunker: TextChunker = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    global _indexer, _embedding_service, _document_extractor, _text_chunker

    logger.info("Initializing Asymptote API...")

    # Initialize shared services
    logger.info("Loading embedding model...")
    _embedding_service = EmbeddingService(model_name=settings.embedding_model)

    _document_extractor = DocumentExtractor()
    _text_chunker = TextChunker(
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
    )

    # Only initialize shared indexer if multi-user mode is disabled
    if not settings.enable_multi_user:
        logger.info(f"Single-user mode: initializing shared vector store")
        if settings.metadata_storage.lower() == "sqlite":
            vector_store = VectorStoreV2(
                index_dir=settings.data_dir / "indexes",
                embedding_dim=_embedding_service.embedding_dim,
            )
        else:
            vector_store = VectorStore(
                index_dir=settings.data_dir / "indexes",
                embedding_dim=_embedding_service.embedding_dim,
            )

        _indexer = DocumentIndexer(
            vector_store=vector_store,
            embedding_service=_embedding_service,
            document_extractor=_document_extractor,
            text_chunker=_text_chunker,
        )
        logger.info(f"Indexed chunks: {vector_store.get_total_chunks()}")
    else:
        logger.info("Multi-user mode enabled: per-user vector stores")

    logger.info("Asymptote API ready")
    logger.info(f"Multi-user mode: {settings.enable_multi_user}")

    yield

    # Cleanup
    logger.info("Shutting down...")
    if _indexer:
        _indexer.save_index()
    logger.info("Shutdown complete")
```

---

## 4. Update Endpoints

### Upload Endpoint

```python
@app.post("/documents/upload", ...)
async def upload_documents(
    files: List[UploadFile] = File(...),
    user_id: Optional[str] = Depends(get_user_id_from_header)
) -> UploadResponse:
    """Upload documents."""
    # ... validation code ...

    # Get user-specific paths
    docs_dir, _ = get_user_storage_paths(user_id)
    indexer = get_user_indexer(user_id)

    for file in files:
        try:
            # Save to user-specific directory
            file_path = docs_dir / file.filename
            with open(file_path, "wb") as f:
                shutil.copyfileobj(file.file, f)

            # Index using user-specific indexer
            doc_metadata = indexer.index_document(file_path, file.filename)
            # ... rest of upload logic

    # Save user's index
    indexer.save_index()
    # ... return response
```

### Search Endpoint

```python
@app.post("/search", ...)
async def search_documents(
    search_request: SearchRequest,
    request: Request,
    user_id: Optional[str] = Depends(get_user_id_from_header)
) -> SearchResponse:
    """Search documents."""
    indexer = get_user_indexer(user_id)
    results = indexer.search(search_request.query, top_k=search_request.top_k)
    # ... rest of search logic
```

### List Documents

```python
@app.get("/documents", ...)
async def list_documents(
    user_id: Optional[str] = Depends(get_user_id_from_header)
) -> DocumentListResponse:
    """List documents."""
    docs_dir, _ = get_user_storage_paths(user_id)
    indexer = get_user_indexer(user_id)

    documents = indexer.list_documents()
    doc_metadata_list = []
    for doc in documents:
        doc_path = docs_dir / doc["filename"]
        # ... rest of list logic using docs_dir
```

### Download Document

```python
@app.get("/documents/{document_id}/pdf", ...)
async def get_pdf(
    document_id: str,
    user_id: Optional[str] = Depends(get_user_id_from_header)
):
    """Download document."""
    docs_dir, _ = get_user_storage_paths(user_id)
    indexer = get_user_indexer(user_id)

    documents = indexer.list_documents()
    doc = next((d for d in documents if d["document_id"] == document_id), None)
    # ...
    doc_path = docs_dir / doc["filename"]
    # ... rest of download logic
```

### Delete Document

```python
@app.delete("/documents/{document_id}", ...)
async def delete_document(
    document_id: str,
    user_id: Optional[str] = Depends(get_user_id_from_header)
):
    """Delete document."""
    docs_dir, _ = get_user_storage_paths(user_id)
    indexer = get_user_indexer(user_id)

    documents = indexer.list_documents()
    # ...
    doc_path = docs_dir / doc["filename"]
    # ... rest of delete logic

    indexer.save_index()
```

---

## 5. Enable Multi-User Mode

In `.env`:

```bash
ENABLE_MULTI_USER=true
```

---

## Complete! 🎉

**What You Get:**

✅ Each browser has a unique user ID
✅ User data stored in `data/users/{user_id}/`
✅ Complete data isolation
✅ No authentication complexity
✅ Perfect for internal deployments

**Test It:**

```bash
# Terminal 1: User A
curl -H "X-User-ID: alice" -F "files=@test.pdf" \
  http://localhost:8000/documents/upload

# Terminal 2: User B
curl -H "X-User-ID: bob" -F "files=@test2.pdf" \
  http://localhost:8000/documents/upload

# Check isolation
ls data/users/alice/documents/  # test.pdf
ls data/users/bob/documents/    # test2.pdf
```

---

**Need the full implementation?** See [MULTIUSER_SIMPLE.md](MULTIUSER_SIMPLE.md) for complete guide.
