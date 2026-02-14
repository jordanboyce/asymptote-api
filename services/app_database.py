"""Application database for persistent configuration and state.

Stores:
- Configuration settings (overrides .env)
- Re-indexing progress/status
- Application state
"""

import sqlite3
import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime

logger = logging.getLogger(__name__)


class AppDatabase:
    """Manages application-level persistent data in SQLite."""

    def __init__(self, db_path: Path = Path("data/app.db")):
        """Initialize application database.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        """Initialize database schema."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS config (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS reindex_jobs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    status TEXT NOT NULL,
                    started_at TEXT NOT NULL,
                    completed_at TEXT,
                    total_documents INTEGER DEFAULT 0,
                    processed_documents INTEGER DEFAULT 0,
                    current_file TEXT,
                    error TEXT,
                    config_snapshot TEXT
                )
            """)

            # AI preferences table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS ai_preferences (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    selected_providers TEXT,
                    rerank_enabled INTEGER DEFAULT 1,
                    synthesize_enabled INTEGER DEFAULT 1,
                    default_provider TEXT,
                    updated_at TEXT NOT NULL
                )
            """)

            # Search history with cached results
            conn.execute("""
                CREATE TABLE IF NOT EXISTS search_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    query TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    top_k INTEGER,
                    results_count INTEGER,
                    ai_provider TEXT,
                    ai_used INTEGER DEFAULT 0,
                    results_json TEXT,
                    execution_time_ms INTEGER
                )
            """)

            # Create index for faster query lookups
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_search_timestamp
                ON search_history(timestamp DESC)
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_search_query
                ON search_history(query)
            """)

            # User preferences table (general key-value store)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS user_preferences (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)

            # Collections table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS collections (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT,
                    color TEXT DEFAULT '#3b82f6',
                    chunk_size INTEGER DEFAULT 500,
                    chunk_overlap INTEGER DEFAULT 50,
                    embedding_model TEXT DEFAULT 'all-MiniLM-L6-v2',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)

            # Document-to-collection mapping
            conn.execute("""
                CREATE TABLE IF NOT EXISTS collection_documents (
                    collection_id TEXT NOT NULL,
                    document_id TEXT NOT NULL,
                    added_at TEXT NOT NULL,
                    PRIMARY KEY (collection_id, document_id),
                    FOREIGN KEY (collection_id) REFERENCES collections(id) ON DELETE CASCADE
                )
            """)

            # Create index for faster lookups
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_collection_documents
                ON collection_documents(collection_id)
            """)

            # Ensure default collection exists
            cursor = conn.execute("SELECT id FROM collections WHERE id = 'default'")
            if not cursor.fetchone():
                timestamp = datetime.utcnow().isoformat()
                conn.execute(
                    """
                    INSERT INTO collections (id, name, description, color, created_at, updated_at)
                    VALUES ('default', 'Default', 'Default document collection', '#3b82f6', ?, ?)
                    """,
                    (timestamp, timestamp)
                )

            conn.commit()
            logger.info(f"Application database initialized at {self.db_path}")

    # Configuration methods
    def get_config(self, key: str, default: Any = None) -> Any:
        """Get configuration value.

        Args:
            key: Configuration key
            default: Default value if not found

        Returns:
            Configuration value (parsed from JSON) or default
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT value FROM config WHERE key = ?",
                (key,)
            )
            row = cursor.fetchone()
            if row:
                try:
                    return json.loads(row[0])
                except json.JSONDecodeError:
                    return row[0]
            return default

    def set_config(self, key: str, value: Any):
        """Set configuration value.

        Args:
            key: Configuration key
            value: Value to store (will be JSON-encoded)
        """
        value_str = json.dumps(value) if not isinstance(value, str) else value
        timestamp = datetime.utcnow().isoformat()

        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO config (key, value, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET
                    value = excluded.value,
                    updated_at = excluded.updated_at
                """,
                (key, value_str, timestamp)
            )
            conn.commit()
            logger.info(f"Config updated: {key} = {value}")

    def get_all_config(self) -> Dict[str, Any]:
        """Get all configuration values.

        Returns:
            Dictionary of all config key-value pairs
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT key, value FROM config")
            config = {}
            for key, value in cursor.fetchall():
                try:
                    config[key] = json.loads(value)
                except json.JSONDecodeError:
                    config[key] = value
            return config

    def delete_config(self, key: str):
        """Delete configuration value.

        Args:
            key: Configuration key to delete
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM config WHERE key = ?", (key,))
            conn.commit()

    # Re-indexing job methods
    def create_reindex_job(self, config_snapshot: Dict[str, Any]) -> int:
        """Create a new re-indexing job.

        Args:
            config_snapshot: Current configuration to use for indexing

        Returns:
            Job ID
        """
        timestamp = datetime.utcnow().isoformat()
        config_json = json.dumps(config_snapshot)

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """
                INSERT INTO reindex_jobs
                (status, started_at, config_snapshot)
                VALUES (?, ?, ?)
                """,
                ("pending", timestamp, config_json)
            )
            conn.commit()
            job_id = cursor.lastrowid
            logger.info(f"Created re-index job {job_id}")
            return job_id

    def update_reindex_job(
        self,
        job_id: int,
        status: Optional[str] = None,
        total_documents: Optional[int] = None,
        processed_documents: Optional[int] = None,
        current_file: Optional[str] = None,
        error: Optional[str] = None,
    ):
        """Update re-indexing job progress.

        Args:
            job_id: Job ID
            status: New status (pending, running, completed, failed)
            total_documents: Total number of documents to process
            processed_documents: Number of documents processed so far
            current_file: Currently processing file
            error: Error message if failed
        """
        updates = []
        params = []

        if status:
            updates.append("status = ?")
            params.append(status)

        if total_documents is not None:
            updates.append("total_documents = ?")
            params.append(total_documents)

        if processed_documents is not None:
            updates.append("processed_documents = ?")
            params.append(processed_documents)

        if current_file is not None:
            updates.append("current_file = ?")
            params.append(current_file)

        if error is not None:
            updates.append("error = ?")
            params.append(error)

        if status in ("completed", "failed"):
            updates.append("completed_at = ?")
            params.append(datetime.utcnow().isoformat())

        if not updates:
            return

        params.append(job_id)
        query = f"UPDATE reindex_jobs SET {', '.join(updates)} WHERE id = ?"

        with sqlite3.connect(self.db_path) as conn:
            conn.execute(query, params)
            conn.commit()

    def get_reindex_job(self, job_id: int) -> Optional[Dict[str, Any]]:
        """Get re-indexing job status.

        Args:
            job_id: Job ID

        Returns:
            Job details or None if not found
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                """
                SELECT id, status, started_at, completed_at,
                       total_documents, processed_documents,
                       current_file, error
                FROM reindex_jobs
                WHERE id = ?
                """,
                (job_id,)
            )
            row = cursor.fetchone()
            if row:
                return dict(row)
            return None

    def get_latest_reindex_job(self) -> Optional[Dict[str, Any]]:
        """Get the most recent re-indexing job.

        Returns:
            Latest job details or None
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                """
                SELECT id, status, started_at, completed_at,
                       total_documents, processed_documents,
                       current_file, error
                FROM reindex_jobs
                ORDER BY id DESC
                LIMIT 1
                """
            )
            row = cursor.fetchone()
            if row:
                return dict(row)
            return None

    def get_active_reindex_job(self) -> Optional[Dict[str, Any]]:
        """Get currently active (pending/running) re-indexing job.

        Returns:
            Active job details or None
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                """
                SELECT id, status, started_at, completed_at,
                       total_documents, processed_documents,
                       current_file, error
                FROM reindex_jobs
                WHERE status IN ('pending', 'running')
                ORDER BY id DESC
                LIMIT 1
                """
            )
            row = cursor.fetchone()
            if row:
                return dict(row)
            return None

    # AI Preferences methods
    def get_ai_preferences(self) -> Optional[Dict[str, Any]]:
        """Get AI preferences.

        Returns:
            AI preferences dict or None
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM ai_preferences WHERE id = 1"
            )
            row = cursor.fetchone()
            if row:
                prefs = dict(row)
                # Parse JSON fields
                if prefs.get('selected_providers'):
                    try:
                        prefs['selected_providers'] = json.loads(prefs['selected_providers'])
                    except json.JSONDecodeError:
                        prefs['selected_providers'] = []
                return prefs
            return None

    def set_ai_preferences(
        self,
        selected_providers: Optional[list] = None,
        rerank_enabled: Optional[bool] = None,
        synthesize_enabled: Optional[bool] = None,
        default_provider: Optional[str] = None
    ):
        """Set AI preferences.

        Args:
            selected_providers: List of selected provider names
            rerank_enabled: Whether reranking is enabled
            synthesize_enabled: Whether synthesis is enabled
            default_provider: Default provider name
        """
        timestamp = datetime.utcnow().isoformat()

        with sqlite3.connect(self.db_path) as conn:
            # Get current preferences
            cursor = conn.execute("SELECT * FROM ai_preferences WHERE id = 1")
            row = cursor.fetchone()

            if row:
                # Update existing
                updates = []
                params = []

                if selected_providers is not None:
                    updates.append("selected_providers = ?")
                    params.append(json.dumps(selected_providers))
                if rerank_enabled is not None:
                    updates.append("rerank_enabled = ?")
                    params.append(1 if rerank_enabled else 0)
                if synthesize_enabled is not None:
                    updates.append("synthesize_enabled = ?")
                    params.append(1 if synthesize_enabled else 0)
                if default_provider is not None:
                    updates.append("default_provider = ?")
                    params.append(default_provider)

                if updates:
                    updates.append("updated_at = ?")
                    params.append(timestamp)
                    params.append(1)  # id

                    query = f"UPDATE ai_preferences SET {', '.join(updates)} WHERE id = ?"
                    conn.execute(query, params)
            else:
                # Insert new
                conn.execute(
                    """
                    INSERT INTO ai_preferences
                    (id, selected_providers, rerank_enabled, synthesize_enabled, default_provider, updated_at)
                    VALUES (1, ?, ?, ?, ?, ?)
                    """,
                    (
                        json.dumps(selected_providers or []),
                        1 if rerank_enabled else 0,
                        1 if synthesize_enabled else 0,
                        default_provider,
                        timestamp
                    )
                )

            conn.commit()
            logger.info("AI preferences updated")

    # Search History methods
    def add_search_history(
        self,
        query: str,
        top_k: int,
        results_count: int,
        ai_provider: Optional[str] = None,
        ai_used: bool = False,
        results_json: Optional[str] = None,
        execution_time_ms: Optional[int] = None
    ) -> int:
        """Add search to history.

        Args:
            query: Search query text
            top_k: Top K parameter used
            results_count: Number of results returned
            ai_provider: AI provider used (if any)
            ai_used: Whether AI was used
            results_json: JSON-encoded results for caching
            execution_time_ms: Execution time in milliseconds

        Returns:
            Search history ID
        """
        timestamp = datetime.utcnow().isoformat()

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """
                INSERT INTO search_history
                (query, timestamp, top_k, results_count, ai_provider, ai_used, results_json, execution_time_ms)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (query, timestamp, top_k, results_count, ai_provider, 1 if ai_used else 0, results_json, execution_time_ms)
            )
            conn.commit()
            return cursor.lastrowid

    def get_search_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent search history.

        Args:
            limit: Maximum number of results

        Returns:
            List of search history entries
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                """
                SELECT id, query, timestamp, top_k, results_count, ai_provider, ai_used, execution_time_ms
                FROM search_history
                ORDER BY timestamp DESC
                LIMIT ?
                """,
                (limit,)
            )
            return [dict(row) for row in cursor.fetchall()]

    def get_search_by_id(self, search_id: int) -> Optional[Dict[str, Any]]:
        """Get search history entry with cached results.

        Args:
            search_id: Search history ID

        Returns:
            Search entry with results_json or None
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM search_history WHERE id = ?",
                (search_id,)
            )
            row = cursor.fetchone()
            if row:
                result = dict(row)
                # Parse results JSON if present
                if result.get('results_json'):
                    try:
                        result['results'] = json.loads(result['results_json'])
                    except json.JSONDecodeError:
                        result['results'] = None
                return result
            return None

    def delete_old_search_history(self, days: int = 30):
        """Delete search history older than specified days.

        Args:
            days: Number of days to keep
        """
        from datetime import timedelta
        cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "DELETE FROM search_history WHERE timestamp < ?",
                (cutoff,)
            )
            deleted = cursor.rowcount
            conn.commit()
            logger.info(f"Deleted {deleted} old search history entries")
            return deleted

    # User Preferences methods
    def get_user_preference(self, key: str, default: Any = None) -> Any:
        """Get user preference value.

        Args:
            key: Preference key
            default: Default value if not found

        Returns:
            Preference value (parsed from JSON) or default
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT value FROM user_preferences WHERE key = ?",
                (key,)
            )
            row = cursor.fetchone()
            if row:
                try:
                    return json.loads(row[0])
                except json.JSONDecodeError:
                    return row[0]
            return default

    def set_user_preference(self, key: str, value: Any):
        """Set user preference value.

        Args:
            key: Preference key
            value: Value to store (will be JSON-encoded)
        """
        value_str = json.dumps(value) if not isinstance(value, str) else value
        timestamp = datetime.utcnow().isoformat()

        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO user_preferences (key, value, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET
                    value = excluded.value,
                    updated_at = excluded.updated_at
                """,
                (key, value_str, timestamp)
            )
            conn.commit()
            logger.info(f"User preference updated: {key}")

    def get_all_user_preferences(self) -> Dict[str, Any]:
        """Get all user preferences.

        Returns:
            Dictionary of all preferences
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT key, value FROM user_preferences")
            prefs = {}
            for key, value in cursor.fetchall():
                try:
                    prefs[key] = json.loads(value)
                except json.JSONDecodeError:
                    prefs[key] = value
            return prefs

    # Collection methods
    def create_collection(
        self,
        name: str,
        description: str = "",
        color: str = "#3b82f6",
        chunk_size: int = 500,
        chunk_overlap: int = 50,
        embedding_model: str = "all-MiniLM-L6-v2"
    ) -> str:
        """Create a new collection.

        Args:
            name: Collection name
            description: Collection description
            color: Hex color for UI display
            chunk_size: Text chunk size for this collection
            chunk_overlap: Chunk overlap for this collection
            embedding_model: Embedding model to use

        Returns:
            Collection ID
        """
        import uuid
        collection_id = str(uuid.uuid4())[:8]
        timestamp = datetime.utcnow().isoformat()

        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO collections
                (id, name, description, color, chunk_size, chunk_overlap, embedding_model, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (collection_id, name, description, color, chunk_size, chunk_overlap, embedding_model, timestamp, timestamp)
            )
            conn.commit()
            logger.info(f"Created collection: {name} ({collection_id})")
            return collection_id

    def get_collection(self, collection_id: str) -> Optional[Dict[str, Any]]:
        """Get collection by ID.

        Args:
            collection_id: Collection ID

        Returns:
            Collection details or None
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM collections WHERE id = ?",
                (collection_id,)
            )
            row = cursor.fetchone()
            if row:
                collection = dict(row)
                # Get document count
                count_cursor = conn.execute(
                    "SELECT COUNT(*) FROM collection_documents WHERE collection_id = ?",
                    (collection_id,)
                )
                collection['document_count'] = count_cursor.fetchone()[0]
                return collection
            return None

    def get_all_collections(self) -> List[Dict[str, Any]]:
        """Get all collections.

        Returns:
            List of collection details
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                """
                SELECT c.*, COUNT(cd.document_id) as document_count
                FROM collections c
                LEFT JOIN collection_documents cd ON c.id = cd.collection_id
                GROUP BY c.id
                ORDER BY c.created_at ASC
                """
            )
            return [dict(row) for row in cursor.fetchall()]

    def update_collection(
        self,
        collection_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        color: Optional[str] = None,
        chunk_size: Optional[int] = None,
        chunk_overlap: Optional[int] = None,
        embedding_model: Optional[str] = None
    ):
        """Update collection settings.

        Args:
            collection_id: Collection ID
            name: New name
            description: New description
            color: New color
            chunk_size: New chunk size
            chunk_overlap: New chunk overlap
            embedding_model: New embedding model
        """
        updates = []
        params = []

        if name is not None:
            updates.append("name = ?")
            params.append(name)
        if description is not None:
            updates.append("description = ?")
            params.append(description)
        if color is not None:
            updates.append("color = ?")
            params.append(color)
        if chunk_size is not None:
            updates.append("chunk_size = ?")
            params.append(chunk_size)
        if chunk_overlap is not None:
            updates.append("chunk_overlap = ?")
            params.append(chunk_overlap)
        if embedding_model is not None:
            updates.append("embedding_model = ?")
            params.append(embedding_model)

        if not updates:
            return

        updates.append("updated_at = ?")
        params.append(datetime.utcnow().isoformat())
        params.append(collection_id)

        query = f"UPDATE collections SET {', '.join(updates)} WHERE id = ?"

        with sqlite3.connect(self.db_path) as conn:
            conn.execute(query, params)
            conn.commit()
            logger.info(f"Updated collection: {collection_id}")

    def delete_collection(self, collection_id: str) -> bool:
        """Delete a collection.

        Args:
            collection_id: Collection ID

        Returns:
            True if deleted, False if collection doesn't exist or is 'default'
        """
        if collection_id == "default":
            logger.warning("Cannot delete default collection")
            return False

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "DELETE FROM collections WHERE id = ?",
                (collection_id,)
            )
            conn.commit()
            deleted = cursor.rowcount > 0
            if deleted:
                logger.info(f"Deleted collection: {collection_id}")
            return deleted

    def add_document_to_collection(self, collection_id: str, document_id: str):
        """Add a document to a collection.

        Args:
            collection_id: Collection ID
            document_id: Document ID
        """
        timestamp = datetime.utcnow().isoformat()

        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO collection_documents
                (collection_id, document_id, added_at)
                VALUES (?, ?, ?)
                """,
                (collection_id, document_id, timestamp)
            )
            conn.commit()

    def remove_document_from_collection(self, collection_id: str, document_id: str):
        """Remove a document from a collection.

        Args:
            collection_id: Collection ID
            document_id: Document ID
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "DELETE FROM collection_documents WHERE collection_id = ? AND document_id = ?",
                (collection_id, document_id)
            )
            conn.commit()

    def get_collection_documents(self, collection_id: str) -> List[str]:
        """Get all document IDs in a collection.

        Args:
            collection_id: Collection ID

        Returns:
            List of document IDs
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT document_id FROM collection_documents WHERE collection_id = ?",
                (collection_id,)
            )
            return [row[0] for row in cursor.fetchall()]

    def get_document_collections(self, document_id: str) -> List[str]:
        """Get all collection IDs that contain a document.

        Args:
            document_id: Document ID

        Returns:
            List of collection IDs
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT collection_id FROM collection_documents WHERE document_id = ?",
                (document_id,)
            )
            return [row[0] for row in cursor.fetchall()]


# Global instance
app_db = AppDatabase()
