"""SQLite-based metadata storage for document chunks."""

import sqlite3
from pathlib import Path
from typing import List, Optional, Dict
import json
import logging

logger = logging.getLogger(__name__)


class MetadataStore:
    """SQLite-based metadata storage for scalability."""

    def __init__(self, db_path: Path):
        """
        Initialize the metadata store.

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
                CREATE TABLE IF NOT EXISTS chunks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    chunk_id TEXT UNIQUE NOT NULL,
                    document_id TEXT NOT NULL,
                    filename TEXT NOT NULL,
                    page_number INTEGER NOT NULL,
                    chunk_index INTEGER NOT NULL,
                    text TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_document_id
                ON chunks(document_id)
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_chunk_id
                ON chunks(chunk_id)
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS documents (
                    document_id TEXT PRIMARY KEY,
                    filename TEXT NOT NULL,
                    num_pages INTEGER NOT NULL,
                    num_chunks INTEGER NOT NULL,
                    upload_timestamp TEXT NOT NULL
                )
            """)

            conn.commit()
            logger.info(f"Initialized metadata database at {self.db_path}")

    def add_chunks(self, chunks: List[dict]):
        """
        Add chunk metadata to the database.

        Args:
            chunks: List of chunk metadata dictionaries
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.executemany("""
                INSERT OR REPLACE INTO chunks
                (chunk_id, document_id, filename, page_number, chunk_index, text)
                VALUES (?, ?, ?, ?, ?, ?)
            """, [
                (
                    chunk["chunk_id"],
                    chunk["document_id"],
                    chunk["filename"],
                    chunk["page_number"],
                    chunk["chunk_index"],
                    chunk["text"]
                )
                for chunk in chunks
            ])
            conn.commit()

        logger.debug(f"Added {len(chunks)} chunks to metadata store")

    def get_chunk_by_index(self, index: int) -> Optional[dict]:
        """
        Get chunk metadata by its sequential index.

        Args:
            index: Sequential index (0-based, matches FAISS index)

        Returns:
            Chunk metadata dictionary or None
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT chunk_id, document_id, filename, page_number, chunk_index, text
                FROM chunks
                ORDER BY id
                LIMIT 1 OFFSET ?
            """, (index,))

            row = cursor.fetchone()
            if row:
                return dict(row)
            return None

    def get_chunks_by_document(self, document_id: str) -> List[dict]:
        """
        Get all chunks for a specific document.

        Args:
            document_id: Document identifier

        Returns:
            List of chunk metadata dictionaries
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT chunk_id, document_id, filename, page_number, chunk_index, text
                FROM chunks
                WHERE document_id = ?
                ORDER BY page_number, chunk_index
            """, (document_id,))

            return [dict(row) for row in cursor.fetchall()]

    def delete_document(self, document_id: str) -> int:
        """
        Delete all chunks for a specific document.

        Args:
            document_id: Document identifier

        Returns:
            Number of chunks deleted
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                DELETE FROM chunks
                WHERE document_id = ?
            """, (document_id,))

            deleted = cursor.rowcount

            conn.execute("""
                DELETE FROM documents
                WHERE document_id = ?
            """, (document_id,))

            conn.commit()

        logger.info(f"Deleted {deleted} chunks for document {document_id}")
        return deleted

    def get_total_chunks(self) -> int:
        """Get total number of chunks in the store."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM chunks")
            return cursor.fetchone()[0]

    def list_documents(self) -> List[dict]:
        """
        List all documents with their statistics.

        Returns:
            List of document metadata dictionaries
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT
                    document_id,
                    filename,
                    COUNT(*) as num_chunks,
                    COUNT(DISTINCT page_number) as num_pages
                FROM chunks
                GROUP BY document_id, filename
                ORDER BY MAX(created_at) DESC
            """)

            return [dict(row) for row in cursor.fetchall()]

    def add_document(self, document_id: str, filename: str, num_pages: int,
                     num_chunks: int, upload_timestamp: str):
        """
        Add document metadata.

        Args:
            document_id: Document identifier
            filename: Original filename
            num_pages: Number of pages
            num_chunks: Number of chunks
            upload_timestamp: ISO timestamp of upload
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO documents
                (document_id, filename, num_pages, num_chunks, upload_timestamp)
                VALUES (?, ?, ?, ?, ?)
            """, (document_id, filename, num_pages, num_chunks, upload_timestamp))
            conn.commit()

    def get_all_chunks_ordered(self) -> List[dict]:
        """
        Get all chunks in order (for migration/initialization).

        Returns:
            List of all chunk metadata dictionaries
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT chunk_id, document_id, filename, page_number, chunk_index, text
                FROM chunks
                ORDER BY id
            """)

            return [dict(row) for row in cursor.fetchall()]

    def document_exists(self, document_id: str) -> bool:
        """
        Check if a document exists in the store.

        Args:
            document_id: Document identifier

        Returns:
            True if document exists
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT 1 FROM chunks WHERE document_id = ? LIMIT 1
            """, (document_id,))
            return cursor.fetchone() is not None

    def get_document_chunk_indices(self, document_id: str) -> List[int]:
        """
        Get the FAISS indices for all chunks of a document.

        Args:
            document_id: Document identifier

        Returns:
            List of chunk indices (0-based, ordered by insertion)
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT (ROW_NUMBER() OVER (ORDER BY id) - 1) as idx
                FROM chunks
                WHERE document_id = ?
                ORDER BY id
            """, (document_id,))

            return [row[0] for row in cursor.fetchall()]

    def clear_all(self):
        """Clear all chunks and documents from the metadata store."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM chunks")
            conn.execute("DELETE FROM documents")
            conn.commit()
            logger.info("Cleared all metadata from database")
