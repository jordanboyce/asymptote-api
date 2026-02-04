# Asymptote API

**Self-hosted semantic search for PDF documents**

Upload PDFs, search their contents using natural language, and get back relevant passages with direct links to the source pages. Runs entirely locally with no external dependencies.

> **Why "Asymptote"?** In mathematics, an asymptote is a line that a curve approaches but never quite reaches. Like semantic search continuously approaching perfect understanding of your documents - getting closer with every query, but always refining, always learning. We're forever approaching the answer, never claiming to have reached it completely.

---

## Table of Contents

- [Quick Start](#quick-start)
- [What It Does](#what-it-does)
- [Technology Stack](#technology-stack)
- [Installation](#installation)
- [Configuration](#configuration)
- [API Usage](#api-usage)
- [Troubleshooting](#troubleshooting)
- [Advanced Topics](#advanced-topics)

---

## Quick Start

### Python (Recommended)

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Start the server
python main.py

# 3. Open your browser
open http://localhost:8000
```

### Docker

```bash
docker-compose up -d
open http://localhost:8000
```

**First time setup**: The embedding model (~90MB) will download automatically on first run.

### What You Get

- **Web Interface**: http://localhost:8000 - Simple UI for searching, uploading, and managing documents
- **API Docs**: http://localhost:8000/docs - Interactive OpenAPI documentation
- **API Endpoint**: http://localhost:8000/api - REST API for programmatic access

---

## What It Does

Asymptote lets you:

1. **Upload PDFs** - Drop in any PDF documents (books, papers, manuals)
2. **Semantic Search** - Ask questions in plain English, not just keywords
3. **Get Results** - Find relevant passages with page numbers and direct PDF links
4. **Scale Up** - Handle hundreds to thousands of documents locally

**Example:**
- Query: *"How do I optimize database queries?"*
- Result: Points you to page 47 of your database textbook with a direct link

---

## Technology Stack

### Core Dependencies

| Package | Version | Purpose | Used In |
|---------|---------|---------|---------|
| **fastapi** | 0.115.5 | Web framework that powers the REST API | `main.py` |
| **uvicorn** | 0.32.1 | ASGI server that runs FastAPI | `main.py` |
| **python-multipart** | 0.0.18 | Handles file uploads (PDFs) | `main.py` |

### PDF Processing

| Package | Version | Purpose | Used In |
|---------|---------|---------|---------|
| **pypdf** | 5.1.0 | Extracts text from standard PDFs | `services/pdf_extractor.py` |
| **pdfplumber** | 0.11.4 | Extracts text from complex layouts (columns, tables) | `services/pdf_extractor.py` |

**Why two PDF libraries?** We try pdfplumber first (handles complex layouts better), then fall back to pypdf if needed.

### Search & Embeddings

| Package | Version | Purpose | Used In |
|---------|---------|---------|---------|
| **sentence-transformers** | 3.3.1 | Converts text to semantic embeddings (vectors) | `services/embedder.py` |
| **faiss-cpu** | 1.9.0 | Fast similarity search over millions of vectors | `services/vector_store.py` |

**What are embeddings?** They convert text to numbers that capture meaning. Similar meanings = similar numbers, enabling semantic search.

### Configuration & Data

| Package | Version | Purpose | Used In |
|---------|---------|---------|---------|
| **pydantic** | 2.10.3 | Data validation for API requests/responses | `models/schemas.py` |
| **pydantic-settings** | 2.6.1 | Loads configuration from `.env` files | `config.py` |
| **python-dotenv** | 1.0.1 | Reads `.env` files | `config.py` |

### Development & Testing

| Package | Version | Purpose | Used In |
|---------|---------|---------|---------|
| **pytest** | 8.3.4 | Testing framework | `tests/` |
| **httpx** | 0.28.1 | HTTP client for testing APIs | `tests/` |

---

## Installation

### Prerequisites

- **Python 3.8+** (check: `python --version`)
- **4GB RAM minimum** (8GB recommended for large collections)
- **500MB disk space** (more for storing PDFs and indexes)

### Step 1: Install Dependencies

```bash
pip install -r requirements.txt
```

**What happens:** Downloads and installs all packages listed above. Takes 2-5 minutes.

### Step 2: Configure (Optional)

```bash
cp .env.example .env
```

**Default settings work fine for most users.** Only edit `.env` if you need to:
- Change the port
- Use a different embedding model
- Adjust chunk sizes
- Choose metadata storage (JSON vs SQLite)

### Step 3: Run the Server

```bash
python main.py
```

**First run:** The embedding model downloads automatically (~90MB, 1-2 minutes).

**You'll see:**
```
INFO - Loading embedding model: all-MiniLM-L6-v2
INFO - Initializing vector store (metadata: json)
INFO - Asymptote API ready
INFO - Uvicorn running on http://0.0.0.0:8000
```

**Access the API:**
- Interactive docs: http://localhost:8000/docs
- Health check: http://localhost:8000/health

### Step 4: Verify Setup

```bash
# Check health
curl http://localhost:8000/health

# Expected response:
{"status":"healthy","indexed_chunks":0}
```

---

## Configuration

Create a `.env` file to customize settings:

```bash
# Data storage
DATA_DIR=./data                          # Where PDFs and indexes are stored

# Embedding model
EMBEDDING_MODEL=all-MiniLM-L6-v2        # Default: fast, 384 dimensions

# Text chunking
CHUNK_SIZE=600                          # Characters per chunk
CHUNK_OVERLAP=100                       # Overlap between chunks

# Search
DEFAULT_TOP_K=10                        # Default number of results
MAX_TOP_K=50                            # Maximum results allowed

# Metadata storage
METADATA_STORAGE=json                   # "json" or "sqlite"

# Server
HOST=0.0.0.0
PORT=8000
```

### Metadata Storage: JSON vs SQLite

**JSON (Default for new users):**
- ✅ Simple, human-readable
- ✅ Good for <100 documents
- ✅ Easy to inspect/debug
- ⚠️ Loads entire file into memory

**SQLite (Recommended for scale):**
- ✅ Handles thousands of documents
- ✅ 50x less memory usage
- ✅ 30x faster startup
- ✅ Better for production

**To switch to SQLite:**
```bash
echo "METADATA_STORAGE=sqlite" >> .env
python main.py
```

**To migrate existing data:**
```bash
python migrate_to_sqlite.py
```

See [METADATA_STORAGE.md](METADATA_STORAGE.md) for details.

---

## API Usage

### Upload Documents

```bash
curl -X POST "http://localhost:8000/documents/upload" \
  -F "files=@document1.pdf" \
  -F "files=@document2.pdf"
```

**Response:**
```json
{
  "message": "Successfully indexed 2 document(s)",
  "documents_processed": 2,
  "total_pages": 45,
  "total_chunks": 123,
  "document_ids": ["abc123", "def456"]
}
```

**What happens:**
1. PDFs are saved to `data/pdfs/`
2. Text is extracted from each page
3. Text is split into overlapping chunks
4. Each chunk is converted to an embedding
5. Embeddings are indexed with FAISS
6. Metadata is saved (JSON or SQLite)

### Search Documents

```bash
curl -X POST "http://localhost:8000/search" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "machine learning algorithms",
    "top_k": 5
  }'
```

**Response:**
```json
{
  "query": "machine learning algorithms",
  "results": [
    {
      "filename": "ml-textbook.pdf",
      "page_number": 42,
      "text_snippet": "Supervised learning algorithms...",
      "similarity_score": 0.87,
      "document_id": "abc123",
      "chunk_id": "abc123_p42_c0",
      "pdf_url": "http://localhost:8000/documents/abc123/pdf",
      "page_url": "http://localhost:8000/documents/abc123/pdf#page=42"
    }
  ],
  "total_results": 5
}
```

**Open PDF at specific page:**
```bash
# In browser (opens at page 42)
open "http://localhost:8000/documents/abc123/pdf#page=42"
```

### List Documents

```bash
curl "http://localhost:8000/documents"
```

### Download PDF

```bash
curl "http://localhost:8000/documents/abc123/pdf" -o output.pdf
```

### Delete Document

```bash
curl -X DELETE "http://localhost:8000/documents/abc123"
```

### Interactive Documentation

Visit http://localhost:8000/docs for a full interactive API playground.

---

## Troubleshooting

### Common Issues

#### 1. "Port 8000 already in use"

**Solution:**
```bash
# Change port in .env
echo "PORT=8001" >> .env
python main.py
```

#### 2. "No module named 'faiss'"

**Solution:**
```bash
pip install -r requirements.txt --force-reinstall
```

**Still failing?**
```bash
# Try installing faiss separately
pip install faiss-cpu
```

#### 3. "Model download is slow"

**Why:** First run downloads ~90MB model from HuggingFace.

**Solutions:**
- Wait 1-2 minutes (one-time download)
- Check your internet connection
- If behind corporate firewall, download manually:
  1. Get model from https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2
  2. Place in `~/.cache/torch/sentence_transformers/`

#### 4. "PDF extraction failed"

**Possible causes:**
- Corrupted PDF
- Scanned images (no text layer)
- Protected/encrypted PDF

**Solutions:**
```bash
# Check PDF with another tool
pdfinfo yourfile.pdf

# Try converting first
pdftk input.pdf output output.pdf
```

#### 5. "Out of memory"

**For large PDFs or many documents:**

```bash
# Reduce chunk size (creates more, smaller chunks)
echo "CHUNK_SIZE=400" >> .env

# Use smaller embedding model
echo "EMBEDDING_MODEL=paraphrase-MiniLM-L3-v2" >> .env

# Switch to SQLite for better memory usage
echo "METADATA_STORAGE=sqlite" >> .env
python migrate_to_sqlite.py
```

#### 6. "Search returns no results"

**Checklist:**
1. Are documents uploaded? Check: `curl http://localhost:8000/documents`
2. Check health: `curl http://localhost:8000/health`
3. Try broader query: "database" instead of "postgresql query optimization"
4. Check logs for errors: Look at terminal output

#### 7. "Docker container crashes"

**Solution:**
```bash
# Check logs
docker-compose logs asymptote

# Increase memory limit in docker-compose.yml
services:
  asymptote:
    mem_limit: 4g
```

### Docker-Specific Issues

#### "Cannot connect to Docker daemon"

```bash
# Start Docker Desktop (Windows/Mac)
# Or start Docker service (Linux)
sudo systemctl start docker
```

#### "Permission denied accessing data folder"

```bash
# Fix permissions
chmod -R 777 ./data
```

#### "Container keeps restarting"

```bash
# Check what's wrong
docker-compose logs -f asymptote

# Common fix: Remove old containers
docker-compose down
docker-compose up -d
```

### Python-Specific Issues

#### "Python version too old"

```bash
# Check version
python --version  # Need 3.8+

# Upgrade Python or use pyenv
pyenv install 3.11
pyenv local 3.11
```

#### "ModuleNotFoundError"

```bash
# Make sure virtual environment is activated
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# Reinstall dependencies
pip install -r requirements.txt
```

#### "Permission denied on Windows"

**Run as administrator or:**
```bash
pip install --user -r requirements.txt
```

---

## Advanced Topics

### Performance & Scalability

**Current capacity:**
- 100-1,000 documents: Works great
- 1,000-10,000 documents: Recommend SQLite metadata storage
- 10,000+ documents: Consider FAISS IVF index or pgvector

**Memory usage estimates:**

| Documents | Chunks | RAM Required |
|-----------|--------|--------------|
| 100       | ~10K   | ~200 MB      |
| 1,000     | ~100K  | ~500 MB      |
| 10,000    | ~1M    | ~3 GB        |

**Speed up indexing:**
```bash
# Larger chunks = fewer chunks = faster
echo "CHUNK_SIZE=1000" >> .env
echo "CHUNK_OVERLAP=150" >> .env
```

### Custom Embedding Models

**Better quality (slower, more memory):**
```bash
echo "EMBEDDING_MODEL=all-mpnet-base-v2" >> .env
```

**Faster (less accurate):**
```bash
echo "EMBEDDING_MODEL=paraphrase-MiniLM-L3-v2" >> .env
```

**See all models:** https://www.sbert.net/docs/pretrained_models.html

### Security Considerations

**This is a local-only service by default. For production:**

1. **Add authentication** (FastAPI supports OAuth2, JWT, API keys)
2. **Restrict CORS** (currently allows all origins)
3. **Use HTTPS** (run behind reverse proxy like nginx)
4. **Rate limiting** (prevent abuse)
5. **Input validation** (check file sizes, types)

**Not recommended for public internet exposure without these protections.**

### Backup & Recovery

**What to backup:**
```bash
# PDFs
data/pdfs/

# FAISS index
data/indexes/faiss.index

# Metadata
data/indexes/metadata.json   # or metadata.db
```

**Backup script:**
```bash
#!/bin/bash
tar -czf asymptote-backup-$(date +%Y%m%d).tar.gz data/
```

**Restore:**
```bash
tar -xzf asymptote-backup-20240203.tar.gz
python main.py
```

---

## Project Structure

```
asymptote/
├── main.py                    # FastAPI app entry point
├── config.py                  # Settings from .env
├── requirements.txt           # Python dependencies
│
├── api/                       # API layer
│   └── routes.py             # Route definitions (deprecated, inline in main.py)
│
├── models/                    # Data models
│   └── schemas.py            # Pydantic request/response models
│
├── services/                  # Business logic
│   ├── pdf_extractor.py      # Extracts text from PDFs
│   ├── chunker.py            # Splits text into chunks
│   ├── embedder.py           # Generates embeddings
│   ├── vector_store.py       # FAISS index (JSON metadata)
│   ├── vector_store_v2.py    # FAISS index (SQLite metadata)
│   ├── metadata_store.py     # SQLite metadata storage
│   └── indexing/
│       └── indexer.py        # Orchestrates indexing pipeline
│
├── tests/                     # Test suite
│   └── test_api.py           # API tests
│
├── data/                      # Runtime data (gitignored)
│   ├── pdfs/                 # Uploaded PDFs
│   └── indexes/              # FAISS + metadata
│
├── .env.example              # Configuration template
├── Dockerfile                # Docker image
├── docker-compose.yml        # Docker setup
├── migrate_to_sqlite.py      # Migrate JSON → SQLite
├── example_usage.py          # Python client example
└── verify_setup.py           # Installation checker
```

---

## Example: Python Client

```python
import requests

BASE_URL = "http://localhost:8000"

# Upload PDFs
with open("document.pdf", "rb") as f:
    response = requests.post(
        f"{BASE_URL}/documents/upload",
        files={"files": f}
    )
    print(response.json())

# Search
response = requests.post(
    f"{BASE_URL}/search",
    json={"query": "machine learning", "top_k": 5}
)
results = response.json()["results"]

# Open first result in browser
if results:
    import webbrowser
    webbrowser.open(results[0]["page_url"])
```

See [example_usage.py](example_usage.py) for more examples.

---

## FAQ

**Q: Can I use this on Windows?**
A: Yes! Python and Docker both work on Windows.

**Q: Does it support other file formats?**
A: Only PDFs currently. DOCX, TXT support planned.

**Q: Can I use it offline?**
A: Yes, after the first run (model downloads once).

**Q: How accurate is semantic search?**
A: Very good for finding concepts, not exact strings. ~80-90% accuracy for most queries.

**Q: Can I delete the embedding model cache?**
A: It's in `~/.cache/torch/sentence_transformers/`. You can delete it but it'll re-download.

**Q: What's the largest PDF it can handle?**
A: Tested up to 1000+ pages. Limited by RAM.

**Q: Can multiple users access it?**
A: Yes, but no built-in auth. Add authentication for multi-user.

---

## License

This project is provided as-is for educational and internal use.

---

## Contributing

This is a reference implementation. Feel free to fork and adapt for your needs.

---

**Asymptote** - Always approaching understanding, never quite reaching it.
