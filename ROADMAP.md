# Asymptote Roadmap

This document outlines planned features and enhancements for future versions of Asymptote.

## Current Status (v1.x)

**Implemented:**
- ✅ Multi-format document support (PDF, TXT, DOCX, CSV)
- ✅ Semantic search with FAISS vector similarity
- ✅ Dual metadata storage (JSON and SQLite)
- ✅ Optional AI enhancements (Claude/OpenAI for reranking and synthesis)
- ✅ Vue 3 web interface with dark mode
- ✅ Windows desktop application with system tray
- ✅ Docker deployment support
- ✅ Corporate SSL certificate handling

---

## Next Revision (v2.0) - Dynamic Configuration & Local AI

### 1. Frontend Configuration Management

**Goal:** Allow users to configure indexing and model settings through the web interface instead of editing config files.

#### 1.1 Embedding Model Selection
- **Feature:** Dropdown or search UI to select embedding models
- **Models to support:**
  - Current: `all-MiniLM-L6-v2` (default, 384 dim)
  - Quality: `all-mpnet-base-v2` (768 dim, slower but more accurate)
  - Speed: `paraphrase-MiniLM-L3-v2` (384 dim, fastest)
  - Multilingual: `paraphrase-multilingual-MiniLM-L12-v2`
  - Custom: Allow entering any sentence-transformers model name
- **Implementation considerations:**
  - Model switching requires re-indexing all documents
  - Show download progress for new models
  - Display model info (size, dimensions, language support)
  - Warn user about re-indexing requirement
  - Store model preference in backend config

**UI Mockup:**
```
Settings Tab > Indexing Configuration
┌─────────────────────────────────────────┐
│ Embedding Model:                        │
│ ┌───────────────────────────────────┐   │
│ │ all-MiniLM-L6-v2 (Current)     ▼ │   │
│ └───────────────────────────────────┘   │
│ Model Info:                             │
│ - Dimensions: 384                       │
│ - Size: ~90 MB                          │
│ - Language: English                     │
│                                         │
│ ⚠️  Changing model requires re-indexing │
│     all documents                       │
│                                         │
│ [Apply and Re-index]                    │
└─────────────────────────────────────────┘
```

#### 1.2 Metadata Storage Toggle
- **Feature:** Switch between JSON and SQLite storage from the UI
- **Functionality:**
  - Radio button or toggle switch
  - Display storage type statistics:
    - JSON: Document count, memory usage estimate
    - SQLite: Document count, database file size
  - Show migration status if switching
  - Auto-migrate data when switching (with progress bar)
  - Warn about performance implications

**UI Mockup:**
```
Settings Tab > Storage Configuration
┌─────────────────────────────────────────┐
│ Metadata Storage:                       │
│ ○ JSON (Simple, <100 docs)              │
│ ● SQLite (Scalable, 1000+ docs)         │
│                                         │
│ Current Storage Stats:                  │
│ - Documents: 127                        │
│ - Database size: 2.4 MB                 │
│ - Index size: 15.3 MB                   │
│                                         │
│ [Switch to JSON] (requires migration)   │
└─────────────────────────────────────────┘
```

#### 1.3 Chunking Configuration
- **Feature:** Adjust chunk size and overlap dynamically
- **Controls:**
  - Chunk size slider (200-2000 characters)
  - Overlap slider (0-500 characters)
  - Visual preview of how many chunks a sample document would create
  - Recommendation based on document collection size
- **Effect:** Requires re-indexing to apply

**UI Mockup:**
```
Settings Tab > Text Chunking
┌─────────────────────────────────────────┐
│ Chunk Size: 600 characters              │
│ ├────────●──────────────┤ (200-2000)    │
│                                         │
│ Overlap: 100 characters                 │
│ ├──●────────────────────┤ (0-500)       │
│                                         │
│ Preview: A 10-page document would       │
│ create ~45 chunks with these settings   │
│                                         │
│ Recommendation: For large collections,  │
│ increase chunk size to reduce memory    │
│                                         │
│ [Apply and Re-index]                    │
└─────────────────────────────────────────┘
```

#### 1.4 Configuration Persistence
- **Backend changes:**
  - New API endpoints:
    - `GET /api/config` - Retrieve current configuration
    - `POST /api/config` - Update configuration (triggers restart if needed)
    - `POST /api/reindex` - Trigger full re-indexing with new settings
  - Store config in database or config file
  - Hot-reload for non-critical settings
  - Server restart trigger for model changes

---

### 2. Online Document Support

**Goal:** Allow users to index documents stored at URLs instead of only uploaded files.

#### 2.1 URL-Based Document Indexing
- **Feature:** Accept URLs to PDF/document files
- **Supported sources:**
  - Direct document URLs (e.g., `https://example.com/paper.pdf`)
  - Cloud storage links (Google Drive, Dropbox, OneDrive with public access)
  - Web pages (extract text content from HTML)
- **Functionality:**
  - Download document to temporary location
  - Extract text using existing DocumentExtractor
  - Store URL as metadata (for re-fetching updates)
  - Option to cache locally or fetch on-demand
  - Support authentication for private URLs (API keys, bearer tokens)

**UI Mockup:**
```
Upload Tab
┌─────────────────────────────────────────┐
│ Upload Method:                          │
│ ● Local Files  ○ URL                    │
│                                         │
│ Document URLs (one per line):           │
│ ┌───────────────────────────────────┐   │
│ │ https://arxiv.org/pdf/2301.00234 │   │
│ │ https://example.com/manual.pdf    │   │
│ │                                   │   │
│ └───────────────────────────────────┘   │
│                                         │
│ ☑ Cache documents locally               │
│ ☐ Require authentication                │
│                                         │
│ [Index URLs]                            │
└─────────────────────────────────────────┘
```

#### 2.2 URL Document Management
- **Features:**
  - Show document source (uploaded vs URL) in documents list
  - "Refresh from URL" button to re-fetch and re-index
  - Automatic periodic refresh option (configurable interval)
  - Handle URL changes (404, moved, etc.)
  - Support URL placeholders for paginated documents

**Backend Implementation:**
- New schema field: `source_type` ("upload" or "url")
- New schema field: `source_url` (null for uploads)
- New field: `last_refreshed` (timestamp for URL documents)
- Download service with retry logic and timeout
- Support for `Range` requests for large files
- Content-Type detection and validation

---

### 3. Ollama Integration

**Goal:** Support local LLM inference via Ollama as an alternative to Anthropic/OpenAI.

#### 3.1 Ollama Detection
- **Feature:** Auto-detect if Ollama is installed and running
- **Implementation:**
  - Check for Ollama API at `http://localhost:11434` on startup
  - Ping `/api/tags` to get available models
  - Show Ollama status in settings UI
  - Fallback gracefully if Ollama is not available

**Detection Logic:**
```python
async def detect_ollama():
    try:
        response = await httpx.get("http://localhost:11434/api/tags", timeout=2.0)
        if response.status_code == 200:
            models = response.json().get("models", [])
            return {"available": True, "models": models}
    except:
        return {"available": False, "models": []}
```

#### 3.2 Ollama as AI Provider
- **Feature:** Add Ollama as a third AI provider option
- **Supported models:**
  - `llama3.2` (Meta's Llama 3.2)
  - `mistral` (Mistral 7B)
  - `phi3` (Microsoft Phi-3)
  - `gemma2` (Google Gemma 2)
  - Any other installed Ollama model
- **Functionality:**
  - Use Ollama for reranking results
  - Use Ollama for answer synthesis
  - No API key required (local inference)
  - Show model selection dropdown (only models actually pulled)

**UI Mockup:**
```
Settings Tab > AI Provider
┌─────────────────────────────────────────┐
│ Provider:                               │
│ ○ Anthropic (Claude)                    │
│ ○ OpenAI (GPT)                          │
│ ● Ollama (Local) ✓ Available           │
│                                         │
│ Ollama Model:                           │
│ ┌───────────────────────────────────┐   │
│ │ llama3.2 (8GB)                 ▼ │   │
│ └───────────────────────────────────┘   │
│                                         │
│ Available Models:                       │
│ - llama3.2 (pulled, 8GB)                │
│ - mistral (pulled, 7GB)                 │
│ - phi3 (not pulled)                     │
│                                         │
│ [Pull New Model]                        │
│                                         │
│ Features:                               │
│ ☑ Reranking (free, local)               │
│ ☑ Synthesis (free, local)               │
└─────────────────────────────────────────┘
```

#### 3.3 Ollama Provider Implementation
- **New class:** `OllamaProvider` extending `AIProvider`
- **Endpoints:**
  - `/api/generate` - For synthesis
  - `/api/chat` - For reranking with conversational context
- **Features:**
  - Streaming support for real-time response
  - Temperature and top_p configuration
  - Context window management (different per model)
  - Performance metrics (tokens/sec, total time)

**Implementation Skeleton:**
```python
class OllamaProvider(AIProvider):
    def __init__(self, base_url: str = "http://localhost:11434"):
        self.base_url = base_url
        self.model = None  # Set by user in settings

    async def validate(self, api_key: str = None) -> bool:
        # Check if Ollama is running and model is available
        pass

    async def complete(self, prompt: str, temperature: float = 0.7) -> str:
        # Call Ollama generate API
        pass

    async def complete_streaming(self, prompt: str):
        # Stream response chunks
        pass
```

#### 3.4 Model Management UI
- **Feature:** Download/manage Ollama models from the UI
- **Functionality:**
  - Browse available models from Ollama registry
  - Show model size before downloading
  - Download progress bar
  - Delete pulled models to free space
  - Show disk space used by models

---

### 4. Additional Enhancements

#### 4.0 Markdown File Support (Quick Win)
- **Add .md file support**
  - Treat as structured text (similar to TXT)
  - Optionally chunk on headers (h1/h2 boundaries)
  - Strip markdown syntax for cleaner embeddings, or keep for context
  - Common use case: AI-generated docs, READMEs, notes

#### 4.1 Search Configuration
- **Feature:** Per-search advanced options
- **Options:**
  - Top K slider (1-100 results)
  - Similarity threshold (filter low-quality results)
  - Date range filter (if documents have timestamps)
  - File type filter (PDF, DOCX, TXT, CSV)
  - Document-specific search (search within one document)

#### 4.2 Performance Monitoring
- **Feature:** Display performance metrics in the UI
- **Metrics:**
  - Search latency (embedding time + FAISS time + AI time)
  - Index size and memory usage
  - Cache hit rate (for repeated queries)
  - AI token usage and cost estimate
  - Embedding model load time

#### 4.3 Batch Operations
- **Feature:** Bulk document management
- **Operations:**
  - Bulk upload from folder (drag & drop folder)
  - Bulk delete with multi-select
  - Export search results as JSON/CSV
  - Backup and restore index
  - Duplicate document detection

#### 4.4 Advanced Chunking Strategies
- **Feature:** Alternative chunking methods
- **Strategies:**
  - Semantic chunking (split on topic boundaries using AI)
  - Sentence-based chunking (keep sentences intact)
  - Paragraph-based chunking
  - Custom delimiter chunking (e.g., split on headers)
  - Recursive chunking for hierarchical documents

---

## Future Considerations (v3.0+)

### 0. Data Persistence Across Versions (Priority)
- **Persistent indexes across updates**
  - Collections and vector indexes should survive application updates without requiring re-indexing
  - Store version metadata (schema version, embedding model version, FAISS index format) alongside data
  - Detect version mismatches on startup and handle gracefully
- **Automatic migration tooling**
  - Migration scripts that run on startup when data format changes
  - Support for incremental migrations (v1 → v2 → v3)
  - Dry-run mode to preview migrations before applying
- **Backup and restore**
  - Export collections with their indexes as portable archives
  - Import collections from backup files
  - CLI tool for backup/restore operations
- **Version compatibility matrix**
  - Document which data formats are compatible with which application versions
  - Warn users before breaking upgrades
  - Option to keep old data directory when upgrading

### 1. Format-Aware Indexing & Search (Priority)
- **Row-level indexing for CSV/tabular data**
  - Each row indexed as its own chunk with headers embedded
  - Metadata stores column names, row number, and raw values
  - Search results render as tables instead of text snippets
  - Unified search across mixed content (PDFs + CSVs in same results)
- **Chunk metadata schema extension**
  - Add `format` field (pdf, txt, docx, csv)
  - Add `columns` and `values` arrays for tabular data
  - Frontend detects format and renders appropriately

### 2. OCR for Image-Based PDFs (Priority)
- **Scanned document support**
  - Detect when PDF pages contain no extractable text
  - Fall back to OCR using pytesseract + pdf2image
  - Support for large collections of scanned document PDFs
  - Optional GPU acceleration with EasyOCR as alternative

### 3. Additional Multi-modal Search
- Support image search (extract text from images with OCR)
- Search within tables and charts
- Audio transcription and search (Whisper integration)

### 4. Advanced AI Features
- Query enhancement (rewrite user queries for better results)
- Multi-hop reasoning (combine info from multiple documents)
- Document summarization (generate executive summaries)
- Question answering with citations

### 5. Collaboration Features
- Multi-user support with authentication
- Shared document collections
- User-specific search history
- Document annotations and highlights

### 6. Enterprise Features
- Role-based access control (RBAC)
- Audit logging
- SSO integration (SAML, OAuth)
- API rate limiting and quotas
- Document retention policies

### 7. Performance & Scaling
- Distributed FAISS index (multiple shards)
- GPU acceleration for embedding generation
- Redis caching layer
- PostgreSQL with pgvector as alternative to FAISS
- Horizontal scaling with load balancer

---

## Implementation Priority

**Phase 1 (Next Release):**
1. Frontend model configuration (highest user value)
2. Ollama integration (popular request, no API costs)
3. Chunking configuration UI

**Phase 2 (Following Release):**
1. Online document support
2. Metadata storage toggle in UI
3. Search configuration options

**Phase 3 (v3.0 - Format & OCR):**
1. Format-aware indexing for CSV/tabular data (row-level chunks, table rendering)
2. OCR for image-based/scanned PDFs (pytesseract + pdf2image)
3. Batch operations
4. Performance monitoring

---

## Technical Debt to Address

1. **Testing:** Expand test suite beyond placeholder tests
2. **Type Hints:** Complete type annotations across all modules
3. **Error Handling:** Improve error messages and user feedback
4. **Documentation:** API documentation for all endpoints
5. **Logging:** Structured logging with levels and rotation
6. **Multi-user Mode:** Either implement or remove the config option
7. **Data Migration:** Tool to move data between storage types seamlessly

---

## Community Feedback

If you have feature requests or suggestions, please open an issue on GitHub or contribute directly!

**Most Requested Features:**
- ✨ Ollama integration (in progress)
- ✨ Frontend configuration (in progress)
- 📄 URL-based document indexing (planned)
- 🎨 More themes/customization (considering)
- 📊 Document analytics and insights (considering)

---

**Last Updated:** 2024-02-12
