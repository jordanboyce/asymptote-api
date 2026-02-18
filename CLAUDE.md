# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Asymptote is a self-hosted semantic search API for documents. It supports PDF, TXT, DOCX, and CSV files, providing semantic search capabilities using sentence transformers and FAISS vector similarity search. The system includes both a FastAPI backend and a Vue 3 frontend with optional AI enhancements (reranking and synthesis) via user-provided Anthropic or OpenAI API keys.

## Common Commands

### Backend (Python)

```bash
# Install dependencies
pip install -r requirements.txt

# Start the development server
python main.py

# Run tests
pytest

# Verify setup
python verify_setup.py
```

### Desktop Application (Windows)

```bash
# Build Windows executable
build_windows.bat

# Create Windows installer
build_installer.bat

# Run desktop app manually
python asymptote_desktop.py

# Run in console mode (no system tray)
python asymptote_desktop.py --no-tray
```

### Frontend (Vue)

```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install

# Start development server (hot reload)
npm run dev

# Build for production (outputs to ../static/)
npm run build

# Preview production build
npm run preview
```

### Docker

```bash
# Start with Docker Compose
docker-compose up -d

# View logs
docker-compose logs -f asymptote

# Stop
docker-compose down
```

## Architecture

### Backend Services Layer

The backend follows a service-oriented architecture with clear separation of concerns:

1. **DocumentExtractor** (`services/document_extractor.py`): Extracts text from documents
   - PDF: Uses `pdfplumber` first (better for complex layouts), falls back to `pypdf`
   - DOCX: Uses `python-docx` to extract paragraphs
   - CSV: Uses `pandas` to convert to readable text format
   - TXT: Direct text reading with encoding detection

2. **TextChunker** (`services/chunker.py`): Splits extracted text into overlapping chunks
   - Configurable chunk size and overlap (default: 600 chars with 100 char overlap)
   - Maintains page number metadata for each chunk

3. **EmbeddingService** (`services/embedder.py`): Converts text to vector embeddings
   - Uses sentence-transformers (default: `all-MiniLM-L6-v2`)
   - Model is cached locally after first download (~90MB)

4. **VectorStore** (`services/vector_store.py`): Manages FAISS index and SQLite metadata
   - SQLite-based metadata storage for scalability
   - FAISS IndexFlatIP for cosine similarity search
   - Constant memory usage regardless of document count

5. **DocumentIndexer** (`services/indexing/indexer.py`): Orchestrates the indexing pipeline
   - Coordinates extraction → chunking → embedding → storage
   - Generates document IDs from SHA256 hash of file content
   - Handles search with optional AI enhancements

6. **AIService** (`services/ai_service.py`): Optional AI enhancements using user-provided API keys
   - Provider abstraction supports both Anthropic and OpenAI
   - Two enhancement features:
     - **Reranking**: Re-orders search results using LLM judgment
     - **Synthesis**: Generates a coherent answer with citations from top results
   - Keys are never stored server-side (passed via `X-AI-Key` header)

### Vector Store Architecture

The vector store uses SQLite for metadata storage:

- **Index directory**: `data/indexes/` (or `data/collections/<id>/indexes/` for collections)
  - `metadata.db`: SQLite database with indexed queries
  - `faiss.index`: FAISS vector index
  - `embeddings.npy`: Raw embeddings for deletion support

### Frontend Architecture

Vue 3 SPA using Composition API with four main components:

1. **SearchTab.vue**: Semantic search interface
   - Query input with optional AI enhancements
   - Results display with similarity scores and page links
   - Keyword highlighting in snippets
   - AI synthesis display when enabled

2. **UploadTab.vue**: Multi-file upload with progress tracking
   - Drag & drop support for PDF, TXT, DOCX, CSV
   - Upload progress bars
   - Success/error feedback

3. **DocumentsTab.vue**: Document management
   - List view of all indexed documents
   - Delete functionality with confirmation
   - Shows page and chunk counts

4. **SettingsTab.vue**: Configuration and AI settings
   - API key management (stored in localStorage)
   - Provider selection (Anthropic/OpenAI)
   - Feature toggles (reranking, synthesis)
   - API key validation

**State Management**: Uses Pinia stores (`frontend/src/stores/`) for shared state

**Styling**: Tailwind CSS 4 with DaisyUI 5 components for UI elements

**Build Process**: Vite builds to `../static/` directory, which FastAPI serves at root path

### API Endpoints

Main routes in `main.py`:

- `POST /documents/upload`: Upload and index documents (supports multiple files)
- `POST /search`: Semantic search with optional AI enhancements
- `GET /documents`: List all indexed documents
- `GET /documents/{document_id}/pdf`: Download/view document file
- `DELETE /documents/{document_id}`: Delete document and all chunks
- `POST /api/ai/validate-key`: Validate AI provider API key
- `GET /health`: Health check endpoint
- `GET /`: Serve web interface

### Configuration

Settings managed via Pydantic in `config.py`:

- `DATA_DIR`: Where documents and indexes are stored (default: `./data`)
- `EMBEDDING_MODEL`: Sentence transformer model name
- `CHUNK_SIZE` / `CHUNK_OVERLAP`: Text chunking parameters
- `DEFAULT_TOP_K` / `MAX_TOP_K`: Search result limits
- `HOST` / `PORT`: Server configuration
- `ENABLE_MULTI_USER`: Enable browser-based user isolation (experimental)

All settings can be overridden via `.env` file (see `.env.example`).

### Data Flow: Document Upload

1. User uploads file(s) via API or web interface
2. File saved to `data/documents/`
3. DocumentExtractor extracts text (page-by-page or section-by-section)
4. TextChunker splits text into overlapping chunks
5. EmbeddingService generates vector embeddings for each chunk
6. VectorStore adds embeddings to FAISS index and saves metadata
7. Response includes document ID, page count, and chunk count

### Data Flow: Search

1. User submits query
2. EmbeddingService generates query embedding
3. VectorStore performs FAISS similarity search
4. If AI enhancements enabled:
   - Optionally rerank results using LLM
   - Optionally synthesize answer from top results
5. Results include filename, page number, text snippet, similarity score, and direct PDF links

### Document ID Generation

Document IDs are generated from SHA256 hash of file content (first 16 characters). This ensures:
- Same file uploaded twice gets same ID (deduplication)
- Different content always gets different ID
- IDs are stable across system restarts

## Key Design Decisions

1. **SQLite Metadata Storage**: Scalable database storage for document metadata
2. **User-Provided AI Keys**: AI features are optional, keys never stored on server
4. **Provider Abstraction**: AIProvider base class allows easy addition of new LLM providers
5. **FAISS Flat Index**: Uses exact search (no quantization) for accuracy over speed
6. **Cosine Similarity**: Computed from L2 distance using formula: `1 - (L2_distance^2 / 2)`
7. **Multi-Format Support**: Document extractor handles PDF, TXT, DOCX, CSV with format-specific extraction logic
8. **Frontend Build Integration**: Vite builds directly to `static/` so FastAPI serves production frontend

## Important File Locations

- **Backend entry point**: `main.py`
- **Configuration**: `config.py` (reads from `.env`)
- **Services**: `services/` directory
  - `document_extractor.py`: Multi-format text extraction
  - `chunker.py`: Text chunking
  - `embedder.py`: Sentence transformer embeddings
  - `vector_store.py`: FAISS + SQLite metadata
  - `ai_service.py`: AI enhancement providers
  - `indexing/indexer.py`: Document indexing orchestration
- **Data models**: `models/schemas.py`
- **Desktop application**: `desktop/` directory
  - `asymptote_desktop.py`: Windows desktop wrapper with system tray
  - `build_windows.bat`: PyInstaller build script
  - `build_installer.bat`: Inno Setup installer script
  - `installer.iss`: Installer configuration
  - `utils/`: Icon generation utilities (development only)
- **Frontend source**: `frontend/src/`
- **Frontend build output**: `static/` (gitignored, generated by `npm run build`)
- **Runtime data**: `data/` (gitignored)
  - `data/documents/`: Uploaded files
  - `data/indexes/`: SQLite metadata and FAISS index

## Deprecated/Removed Files (As of Latest Cleanup)

The following files were removed during code cleanup and should not be referenced:
- ~~`api/routes.py`~~ - Removed (redundant, all routes in `main.py`)
- ~~`api/`~~ - Directory removed (empty, only had `__init__.py`)
- ~~`services/pdf_extractor.py`~~ - Removed (superseded by `document_extractor.py`)
- ~~`services/vector_store_v2.py`~~ - Removed (merged into `vector_store.py`, now SQLite-only)
- ~~`data/pdfs/`~~ - Renamed to `data/documents/` for multi-format support
- ~~`migrate_to_sqlite.py`~~ - Removed (outdated, referenced old non-collection paths)

## Development Notes

### Adding New Document Formats

To add support for a new document format:

1. Add extraction logic to `DocumentExtractor` class in `services/document_extractor.py`
2. Return a list of strings (one per page/section) like existing extractors
3. Add file extension to `SUPPORTED_EXTENSIONS` in `main.py` upload endpoint
4. Update frontend file picker in `UploadTab.vue` to accept new extension

### Adding New AI Providers

To add a new LLM provider:

1. Create a new provider class inheriting from `AIProvider` in `services/ai_service.py`
2. Implement `complete()` and `validate()` methods
3. Add provider to `create_provider()` factory function
4. Update frontend `SettingsTab.vue` to include new provider option

### Testing

The test suite is minimal (placeholder tests in `tests/test_api.py`). To add real tests:

1. Import the FastAPI app from `main.py`
2. Use `TestClient` from `fastapi.testclient`
3. Create sample documents in `tests/fixtures/`
4. Test upload, search, delete flows

### Frontend Development

When working on the frontend:

1. Run backend separately: `python main.py`
2. Run frontend dev server: `cd frontend && npm run dev`
3. Frontend dev server proxies API requests to backend (configured in `vite.config.js`)
4. Hot reload works automatically
5. Build for production with `npm run build` before committing UI changes

### Memory Considerations

- SQLite metadata storage provides constant memory usage regardless of document count
- Embedding model is loaded once on startup and stays in memory
- FAISS index is memory-mapped for large indexes

## Code Cleanup Summary (Latest)

Recent cleanup simplified the codebase to use SQLite-only storage:

**Files Removed:**
1. `api/routes.py` - Completely unused, redundant with routes in `main.py`
2. `api/` directory - Empty directory, only contained `__init__.py`
3. `services/pdf_extractor.py` - Superseded by `DocumentExtractor`
4. `services/vector_store_v2.py` - Merged into `vector_store.py` (SQLite-only)
5. `migrate_to_sqlite.py` - No longer needed (SQLite is now the only option)

**Files Updated:**
1. `config.py` - Removed `metadata_storage` option (SQLite-only now)
2. `services/vector_store.py` - Now uses SQLite exclusively (renamed from v2)
3. `services/indexer_manager.py` - Simplified to use single VectorStore
4. `services/reindex_service.py` - Removed storage type switching
5. `services/config_manager.py` - Removed metadata_storage from configurable fields
6. `services/backup_service.py` - Removed storage type references
7. `verify_setup.py` - Updated imports

**Directory Structure:**
- Index storage: `data/indexes/` (contains `faiss.index`, `metadata.db`, `embeddings.npy`)
- For collections: `data/collections/<id>/indexes/`

**Remaining Considerations:**
- Multi-user mode (`enable_multi_user` config) is not yet implemented
- Test suite in `tests/` contains only placeholder tests
- Legacy data may exist in `data/indexes/` root (pre-cleanup) that should be in subdirectories
