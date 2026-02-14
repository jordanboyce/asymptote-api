# Asymptote v2.0 Implementation Status

## Overview
This document tracks the implementation progress of v2.0 features including:
- Frontend configuration management
- Ollama integration
- Dynamic model selection
- Chunking configuration

---

## Backend Implementation ✅ COMPLETE

### 1. Ollama Provider (`services/ai_service.py`)
**Status:** ✅ Complete

**Changes Made:**
- Added `OllamaProvider` class extending `AIProvider`
- Implements `complete()` and `validate()` methods
- Supports configurable base_url and model selection
- Added `detect_ollama()` utility function to check availability and list models
- Updated `create_provider()` factory to support Ollama (no API key needed)

**Key Features:**
- Automatic model detection via `/api/tags` endpoint
- Token estimation (Ollama doesn't provide exact counts)
- Timeout handling (120s for completion, 5s for validation)
- Support for any Ollama model (llama3.2, mistral, phi3, etc.)

### 2. Configuration Manager (`services/config_manager.py`)
**Status:** ✅ Complete

**New Service:**
- `ConfigManager` class for runtime configuration management
- Reads/writes `.env` file for persistent changes
- Validates configuration updates
- Determines if restart/reindex is required
- Caches config for post-restart comparison

**Methods:**
- `get_current_config()` - Returns all current settings
- `update_config(updates)` - Updates config and .env file
- `get_embedding_models()` - Lists recommended models with specs
- `_update_env_file(updates)` - Persists changes to .env
- `_cache_config(updates)` - Caches for restart detection

**Managed Settings:**
- `embedding_model` - Model name (requires restart + reindex)
- `chunk_size` - Characters per chunk (requires reindex)
- `chunk_overlap` - Overlap size (requires reindex)
- `metadata_storage` - JSON vs SQLite (requires restart)
- `default_top_k`, `max_top_k` - Search limits (live update)

### 3. API Endpoints (`main.py`)
**Status:** ✅ Complete

**New Endpoints:**

#### Configuration Management
- `GET /api/config` - Get current configuration
- `POST /api/config` - Update configuration settings
- `GET /api/config/embedding-models` - List available models

#### Ollama Integration
- `GET /api/ollama/status` - Check if Ollama is running + list models
- `POST /api/ollama/validate` - Validate specific model availability

**Updated Endpoints:**
- `POST /api/ai/validate-key` - Now supports Ollama validation (no key needed)
  - Added `X-Ollama-Model` header support
  - Handles cloud providers (API key required) and Ollama (no key)

- `POST /search` - Now supports Ollama for AI enhancements
  - Added `X-Ollama-Model` header parameter
  - Creates Ollama provider when `ai.provider === 'ollama'`
  - No API key required for Ollama searches

**Header Parameters:**
```
Cloud providers (Anthropic/OpenAI):
  X-AI-Key: sk-... (required)
  X-AI-Provider: anthropic|openai

Ollama:
  X-AI-Provider: ollama
  X-Ollama-Model: llama3.2 (or any installed model)
```

---

## Frontend Implementation 🚧 IN PROGRESS

### 1. Configuration Tab (New Component)
**Status:** 🚧 TODO

**File:** `frontend/src/components/ConfigTab.vue`

**Sections:**

#### A. Embedding Model Selection
- Dropdown/searchable select for model choice
- Model cards showing:
  - Name and description
  - Dimensions (384, 768, etc.)
  - Size in MB
  - Speed rating (fast, medium, slow)
  - Quality rating (good, better, best)
  - Language support
- Current model indicator
- Warning about reindex requirement
- "Apply & Re-index" button

**Data Flow:**
```
GET /api/config/embedding-models → Display options
User selects model → Shows reindex warning
User confirms → POST /api/config {embedding_model: "..."}
Backend returns {requires_restart: true, requires_reindex: true}
Show restart instruction → User restarts server
Show reindex progress (future: automated via WebSocket)
```

#### B. Chunking Configuration
- Slider for chunk size (200-2000 chars)
- Slider for overlap (0-500 chars)
- Live preview: "A 10-page doc → ~45 chunks"
- Current values display
- Recommendations based on collection size
- "Apply & Re-index" button

**Data Flow:**
```
GET /api/config → Display current chunk_size, chunk_overlap
User adjusts sliders → Update preview calculation
User clicks apply → POST /api/config {chunk_size: X, chunk_overlap: Y}
Show reindex required message
```

#### C. Metadata Storage Toggle
- Radio buttons: JSON vs SQLite
- Storage stats:
  - Document count
  - Index size
  - Memory estimate (JSON) or DB file size (SQLite)
- Migration status/progress
- "Switch & Migrate" button

**Data Flow:**
```
GET /api/config → Show current metadata_storage
User selects different option → Show migration warning
User confirms → POST /api/config {metadata_storage: "sqlite"}
Backend returns {requires_restart: true}
Show restart instruction
```

### 2. Settings Tab Updates (Ollama Integration)
**Status:** 🚧 TODO

**File:** `frontend/src/components/SettingsTab.vue`

**Changes:**

#### A. Add Ollama Provider Option
Update provider selection to include three options:
```vue
<button @click="setProvider('anthropic')">Anthropic</button>
<button @click="setProvider('openai')">OpenAI</button>
<button @click="setProvider('ollama')">Ollama (Local)</button>
```

#### B. Ollama Status Detection
```javascript
async checkOllamaStatus() {
  const response = await fetch('/api/ollama/status')
  const data = await response.json()
  this.ollamaAvailable = data.available
  this.ollamaModels = data.models
}
```

#### C. Ollama Model Selection
When provider === 'ollama':
- Show model dropdown (only if Ollama is available)
- List installed models from `/api/ollama/status`
- Show model sizes
- "Pull New Model" button (future: trigger ollama pull)
- No API key field (hide or replace with model selector)

#### D. Conditional UI
```vue
<div v-if="aiSettings.provider === 'ollama'">
  <div v-if="!ollamaAvailable" class="alert alert-warning">
    Ollama not detected. Install from https://ollama.com
  </div>
  <div v-else>
    <label>Select Model</label>
    <select v-model="selectedOllamaModel">
      <option v-for="model in ollamaModels" :value="model.name">
        {{ model.name }} ({{ formatBytes(model.size) }})
      </option>
    </select>
  </div>
</div>

<div v-else>
  <!-- Existing API key input for cloud providers -->
</div>
```

#### E. Validation Updates
Update `validateAndSaveKey()`:
```javascript
async validateAndSaveKey() {
  if (this.aiSettings.provider === 'ollama') {
    // Validate Ollama model
    const response = await fetch('/api/ollama/validate', {
      method: 'POST',
      body: JSON.stringify({ model_name: this.selectedOllamaModel })
    })
    const data = await response.json()
    // Save model to localStorage
    localStorage.setItem('ollama_model', this.selectedOllamaModel)
  } else {
    // Existing cloud provider validation
  }
}
```

### 3. Search Tab Updates
**Status:** 🚧 TODO

**File:** `frontend/src/components/SearchTab.vue`

**Changes:**

#### A. Ollama Header Support
Update search request to include Ollama model when provider is Ollama:
```javascript
const headers = {
  'Content-Type': 'application/json'
}

if (ai.provider === 'ollama') {
  headers['X-AI-Provider'] = 'ollama'
  headers['X-Ollama-Model'] = localStorage.getItem('ollama_model') || 'llama3.2'
} else {
  headers['X-AI-Key'] = getStoredKey(ai.provider)
  headers['X-AI-Provider'] = ai.provider
}
```

#### B. Free AI Badge
When using Ollama, show a badge indicating "Free - Local AI":
```vue
<span v-if="ai.provider === 'ollama'" class="badge badge-success">
  🆓 Local AI
</span>
```

### 4. App Structure Updates
**Status:** 🚧 TODO

**File:** `frontend/src/App.vue`

**Changes:**
- Add new "Configuration" tab between "Upload" and "Settings"
- Update tab navigation to include ConfigTab
- Import and register ConfigTab component

```vue
<template>
  <div class="tabs">
    <a @click="currentTab = 'search'">Search</a>
    <a @click="currentTab = 'upload'">Upload</a>
    <a @click="currentTab = 'documents'">Documents</a>
    <a @click="currentTab = 'config'">Configuration</a> <!-- NEW -->
    <a @click="currentTab = 'settings'">Settings</a>
  </div>

  <component :is="tabComponents[currentTab]" />
</template>

<script>
import ConfigTab from './components/ConfigTab.vue' // NEW

const tabComponents = {
  search: SearchTab,
  upload: UploadTab,
  documents: DocumentsTab,
  config: ConfigTab, // NEW
  settings: SettingsTab
}
</script>
```

---

## Re-indexing Functionality 🚧 TODO

### Backend: Re-index Endpoint
**File:** `main.py`

**New Endpoint:**
```python
@app.post("/api/reindex", tags=["admin"])
async def reindex_all_documents(
    background_tasks: BackgroundTasks,
    indexer: DocumentIndexer = Depends(get_indexer)
):
    """
    Re-index all documents with current configuration.

    Returns immediately with a task ID. Use GET /api/reindex/status/{task_id}
    to check progress.

    Useful after changing embedding model or chunking parameters.
    """
    # Clear existing index
    # Re-index all files in data/documents/
    # Return task_id for progress tracking
    pass
```

### Frontend: Re-index UI
**Component:** `ConfigTab.vue`

**Features:**
- Progress bar showing % complete
- Current file being processed
- Estimated time remaining
- Pause/resume/cancel buttons
- WebSocket or polling for live updates

---

## Testing Checklist 🚧 TODO

### Backend Tests
- [ ] Ollama provider creates successfully
- [ ] Ollama validation detects running Ollama
- [ ] Ollama validation fails gracefully when not running
- [ ] Config manager updates .env file correctly
- [ ] Config manager identifies restart requirements
- [ ] Config manager identifies reindex requirements
- [ ] Search endpoint accepts Ollama provider
- [ ] Search endpoint works without API key for Ollama
- [ ] Ollama status endpoint returns correct data

### Frontend Tests
- [ ] Configuration tab renders correctly
- [ ] Embedding model dropdown displays all models
- [ ] Chunking sliders work and show preview
- [ ] Ollama status detection works
- [ ] Ollama provider selection shows model dropdown
- [ ] Ollama provider hides API key field
- [ ] Search with Ollama sends correct headers
- [ ] Settings persist across page reloads

### Integration Tests
- [ ] Full workflow: Change model → restart → reindex → search works
- [ ] Full workflow: Switch to Ollama → select model → search with AI works
- [ ] Full workflow: Adjust chunking → reindex → search quality improves

---

## Deployment Notes

### New Dependencies
- **httpx** - Already in requirements.txt ✅
- No new npm packages required ✅

### Configuration Changes
- New fields in `.env`:
  - None (all existing fields are now editable via UI)

### Migration Path
1. Pull latest code
2. Restart server (picks up new endpoints)
3. Optional: Install Ollama for local AI
4. Use UI to configure settings
5. Re-index if changing models/chunking

---

## Future Enhancements (v2.1+)

### Advanced Features
- [ ] Automatic Ollama model download from UI
- [ ] Ollama model management (delete, update)
- [ ] Custom embedding model upload
- [ ] Semantic chunking (AI-powered topic detection)
- [ ] Background reindexing with WebSocket progress
- [ ] Configuration history/rollback
- [ ] A/B testing different models on same queries

### Performance
- [ ] Batch reindexing for large collections
- [ ] Incremental reindexing (only changed docs)
- [ ] Parallel document processing
- [ ] Caching for repeated model loads

---

**Last Updated:** 2024-02-12
**Status:** Backend Complete ✅ | Frontend In Progress 🚧
