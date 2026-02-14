# Asymptote v2.0 - Critical Fixes

## Issues Identified and Resolved

### Problem 1: Configuration Doesn't Persist
**Issue:** Configuration changes were written to `.env` file but required manual server restart. Changes were lost if server restarted before `.env` was updated.

**Solution:** Implemented SQLite-based application database for persistent configuration.

**Files Created:**
- `services/app_database.py` - Application database service
  - `config` table for configuration key-value storage
  - `reindex_jobs` table for tracking re-indexing progress
  - Automatic schema initialization

**Files Modified:**
- `services/config_manager.py`
  - Now uses database as primary storage
  - `.env` file updated as backup
  - `get_current_config()` merges database values with `.env` defaults
  - Database values take precedence

**Benefits:**
- ✅ Configuration persists across restarts
- ✅ No manual server restart needed for some settings
- ✅ Database is source of truth
- ✅ `.env` remains as fallback/default values

---

### Problem 2: No Re-indexing Mechanism
**Issue:** Users could change embedding model or chunking settings, but had no way to re-index existing documents to apply the changes.

**Solution:** Implemented background re-indexing service with progress tracking.

**Files Created:**
- `services/reindex_service.py` - Background re-indexing service
  - Async re-indexing in background
  - Progress tracking (documents processed, current file)
  - Configuration snapshot for consistent indexing
  - Error handling and recovery

**API Endpoints Added:**
- `POST /api/reindex` - Start re-indexing job
  - Returns job ID immediately
  - Runs in background
  - Uses current configuration from database

- `GET /api/reindex/status?job_id=123` - Check progress
  - Real-time progress (% complete)
  - Current file being processed
  - Total vs processed document counts
  - Error details if failed

**Benefits:**
- ✅ Users can apply configuration changes
- ✅ Progress tracking with real-time updates
- ✅ Non-blocking (returns immediately)
- ✅ Safe (uses configuration snapshot)
- ✅ Prevents concurrent re-indexing jobs

---

## Database Schema

### Application Database (`data/app.db`)

#### Table: `config`
```sql
CREATE TABLE config (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,           -- JSON-encoded value
    updated_at TEXT NOT NULL        -- ISO 8601 timestamp
)
```

**Purpose:** Store configuration overrides that take precedence over `.env`

**Example Data:**
```
key                 | value            | updated_at
--------------------|------------------|-------------------------
embedding_model     | "all-mpnet..."   | 2024-02-12T10:30:00
chunk_size          | 800              | 2024-02-12T10:30:00
chunk_overlap       | 150              | 2024-02-12T10:30:00
```

#### Table: `reindex_jobs`
```sql
CREATE TABLE reindex_jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    status TEXT NOT NULL,                    -- pending, running, completed, failed
    started_at TEXT NOT NULL,
    completed_at TEXT,
    total_documents INTEGER DEFAULT 0,
    processed_documents INTEGER DEFAULT 0,
    current_file TEXT,
    error TEXT,
    config_snapshot TEXT                     -- JSON of config used for this job
)
```

**Purpose:** Track re-indexing jobs with progress

**Example Data:**
```
id | status    | started_at          | total_docs | processed_docs | current_file
---|-----------|---------------------|------------|----------------|-------------
1  | completed | 2024-02-12T10:31:00 | 127        | 127            | NULL
2  | running   | 2024-02-12T11:15:00 | 127        | 45             | report.pdf
```

---

## API Reference

### Configuration with Persistence

#### GET /api/config
Returns merged configuration (database + .env):
```json
{
  "embedding_model": "all-mpnet-base-v2",  // from database
  "chunk_size": 800,                        // from database
  "chunk_overlap": 150,                     // from database
  "metadata_storage": "json",               // from .env (not changed)
  "default_top_k": 10,
  "max_top_k": 50
}
```

#### POST /api/config
Saves to database AND .env:
```bash
curl -X POST http://localhost:8000/api/config \
  -H "Content-Type: application/json" \
  -d '{
    "embedding_model": "all-mpnet-base-v2",
    "chunk_size": 800,
    "chunk_overlap": 150
  }'
```

Response:
```json
{
  "success": true,
  "requires_restart": true,      // embedding model change needs restart
  "requires_reindex": true,       // both model and chunking need reindex
  "updated_fields": ["embedding_model", "chunk_size", "chunk_overlap"],
  "errors": []
}
```

### Re-indexing

#### POST /api/reindex
Start background re-indexing:
```bash
curl -X POST http://localhost:8000/api/reindex
```

Response:
```json
{
  "job_id": 5,
  "status": "started",
  "message": "Re-indexing job started in background"
}
```

Error (if job already running):
```json
{
  "detail": "Re-indexing job 4 is already running"
}
```

#### GET /api/reindex/status?job_id=5
Check progress:
```bash
# Specific job
curl http://localhost:8000/api/reindex/status?job_id=5

# Latest job (if job_id omitted)
curl http://localhost:8000/api/reindex/status
```

Response (running):
```json
{
  "id": 5,
  "status": "running",
  "started_at": "2024-02-12T11:15:00.123Z",
  "completed_at": null,
  "total_documents": 127,
  "processed_documents": 45,
  "current_file": "machine-learning-textbook.pdf",
  "error": null,
  "progress_percent": 35.4
}
```

Response (completed):
```json
{
  "id": 5,
  "status": "completed",
  "started_at": "2024-02-12T11:15:00.123Z",
  "completed_at": "2024-02-12T11:22:35.456Z",
  "total_documents": 127,
  "processed_documents": 127,
  "current_file": null,
  "error": null,
  "progress_percent": 100.0
}
```

Response (failed):
```json
{
  "id": 5,
  "status": "failed",
  "started_at": "2024-02-12T11:15:00.123Z",
  "completed_at": "2024-02-12T11:18:22.789Z",
  "total_documents": 127,
  "processed_documents": 23,
  "current_file": "corrupted.pdf",
  "error": "Failed to extract text from corrupted.pdf: Invalid PDF structure",
  "progress_percent": 18.1
}
```

---

## Complete Workflow Examples

### Example 1: Change Embedding Model

1. **Update Config:**
   ```bash
   curl -X POST http://localhost:8000/api/config \
     -H "Content-Type: application/json" \
     -d '{"embedding_model": "all-mpnet-base-v2"}'
   ```

   Response indicates `requires_restart: true` and `requires_reindex: true`.

2. **Restart Server:**
   ```bash
   # Stop server (Ctrl+C)
   python main.py
   ```

   Server loads new model on startup.

3. **Start Re-indexing:**
   ```bash
   curl -X POST http://localhost:8000/api/reindex
   ```

   Returns `{"job_id": 6, ...}`

4. **Monitor Progress:**
   ```bash
   # Poll every few seconds
   while true; do
     curl http://localhost:8000/api/reindex/status?job_id=6
     sleep 2
   done
   ```

5. **Done!**
   All documents now indexed with new model.

### Example 2: Adjust Chunking (No Restart)

1. **Update Config:**
   ```bash
   curl -X POST http://localhost:8000/api/config \
     -H "Content-Type: application/json" \
     -d '{"chunk_size": 800, "chunk_overlap": 150}'
   ```

   Response shows `requires_restart: false` but `requires_reindex: true`.

2. **Start Re-indexing (No Restart Needed):**
   ```bash
   curl -X POST http://localhost:8000/api/reindex
   ```

3. **Monitor and Done!**

### Example 3: Frontend Integration

```javascript
// User clicks "Apply Chunking Changes" button

// 1. Update config
const configResponse = await axios.post('/api/config', {
  chunk_size: 800,
  chunk_overlap: 150
})

if (configResponse.data.requires_reindex) {
  // 2. Ask user if they want to re-index now
  if (confirm('Re-index all documents now?')) {
    // 3. Start re-indexing
    const reindexResponse = await axios.post('/api/reindex')
    const jobId = reindexResponse.data.job_id

    // 4. Poll for progress
    const interval = setInterval(async () => {
      const status = await axios.get(`/api/reindex/status?job_id=${jobId}`)

      // Update progress bar
      progressBar.value = status.data.progress_percent
      currentFile.value = status.data.current_file

      // Check if done
      if (status.data.status === 'completed') {
        clearInterval(interval)
        alert('Re-indexing complete!')
      } else if (status.data.status === 'failed') {
        clearInterval(interval)
        alert(`Re-indexing failed: ${status.data.error}`)
      }
    }, 2000) // Poll every 2 seconds
  }
}
```

---

## Migration Notes

### From v2.0 (without fixes) to v2.0.1 (with fixes)

1. **Database Auto-Created:**
   - `data/app.db` created automatically on first run
   - No migration needed

2. **Existing .env Still Works:**
   - Values in `.env` are used as defaults
   - Can override any setting via UI
   - Database overrides take precedence

3. **No Breaking Changes:**
   - All existing endpoints work identically
   - New endpoints are additions only

---

## Future Enhancements

1. **Real-time Progress (WebSocket):**
   - Currently: Poll `/api/reindex/status` every few seconds
   - Future: WebSocket for real-time updates

2. **Pause/Resume/Cancel:**
   - Currently: Job runs to completion or failure
   - Future: Allow user to pause/resume/cancel

3. **Incremental Re-indexing:**
   - Currently: Re-indexes all documents
   - Future: Only re-index documents that changed

4. **Batch Re-indexing:**
   - Currently: Processes documents sequentially
   - Future: Parallel processing for speed

5. **Configuration History:**
   - Track all config changes
   - Rollback to previous configurations
   - Diff between versions

---

## Testing Checklist

- [ ] Configuration persists across server restarts
- [ ] Database overrides work correctly
- [ ] `.env` values used as defaults
- [ ] Re-indexing starts successfully
- [ ] Progress updates correctly
- [ ] Current file shows in status
- [ ] Re-indexing completes successfully
- [ ] Cannot start multiple jobs simultaneously
- [ ] Errors handled gracefully
- [ ] Failed jobs show error message
- [ ] Configuration changes applied after re-index

---

**Status:** ✅ Complete
**Version:** 2.0.1 (Critical Fixes)
**Date:** 2024-02-12
