"""Configuration management service for dynamic settings updates.

Handles runtime configuration changes including:
- Embedding model selection
- Chunking parameters
- Metadata storage type
- Other indexing settings

Configuration is stored in SQLite database for persistence across restarts.
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from config import Settings, settings
from services.app_database import app_db

logger = logging.getLogger(__name__)


class ConfigManager:
    """Manages dynamic configuration updates with database persistence."""

    def __init__(self, env_file: Path = Path(".env")):
        self.env_file = env_file

    def get_current_config(self) -> Dict[str, Any]:
        """Get current configuration values.

        Merges database overrides with .env defaults.
        Database values take precedence.
        """
        # Start with current settings from .env
        config = {
            "embedding_model": settings.embedding_model,
            "chunk_size": settings.chunk_size,
            "chunk_overlap": settings.chunk_overlap,
            "metadata_storage": settings.metadata_storage,
            "default_top_k": settings.default_top_k,
            "max_top_k": settings.max_top_k,
            "data_dir": str(settings.data_dir),
            "host": settings.host,
            "port": settings.port,
        }

        # Override with database values if present
        db_config = app_db.get_all_config()
        for key in config.keys():
            if key in db_config:
                config[key] = db_config[key]

        return config

    def update_config(self, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Update configuration values.

        Args:
            updates: Dictionary of config key-value pairs to update

        Returns:
            Dictionary with:
                - success (bool): Whether update succeeded
                - requires_restart (bool): Whether server restart is needed
                - requires_reindex (bool): Whether re-indexing is needed
                - updated_fields (list): List of fields that were updated
                - errors (list): List of error messages if any
        """
        result = {
            "success": True,
            "requires_restart": False,
            "requires_reindex": False,
            "updated_fields": [],
            "errors": [],
        }

        # Fields that require restart
        restart_fields = {"embedding_model", "metadata_storage", "host", "port"}
        # Fields that require re-indexing
        reindex_fields = {"embedding_model", "chunk_size", "chunk_overlap"}

        # Validate updates
        valid_fields = {
            "embedding_model", "chunk_size", "chunk_overlap",
            "metadata_storage", "default_top_k", "max_top_k"
        }

        for key in updates.keys():
            if key not in valid_fields:
                result["errors"].append(f"Invalid config field: {key}")
                result["success"] = False

        if not result["success"]:
            return result

        # Store in database (primary persistence)
        try:
            for key, value in updates.items():
                app_db.set_config(key, value)
        except Exception as e:
            result["errors"].append(f"Failed to update database: {e}")
            result["success"] = False
            return result

        # Also update .env file for restart compatibility
        try:
            self._update_env_file(updates)
        except Exception as e:
            # Non-fatal - database is source of truth
            logger.warning(f"Failed to update .env file: {e}")

        # Update runtime settings (for non-restart fields)
        for key, value in updates.items():
            if key in restart_fields:
                result["requires_restart"] = True
            if key in reindex_fields:
                result["requires_reindex"] = True

            result["updated_fields"].append(key)

            # Update runtime settings if no restart required
            if key not in restart_fields:
                try:
                    setattr(settings, key, value)
                except Exception as e:
                    result["errors"].append(f"Failed to update {key}: {e}")
                    result["success"] = False

        return result

    def _update_env_file(self, updates: Dict[str, Any]):
        """Update .env file with new values."""
        env_lines = []

        # Read existing .env file if it exists
        if self.env_file.exists():
            with open(self.env_file, "r") as f:
                env_lines = f.readlines()

        # Convert updates to uppercase env var names
        env_updates = {k.upper(): str(v) for k, v in updates.items()}

        # Update or append values
        updated_keys = set()
        for i, line in enumerate(env_lines):
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            if "=" in line:
                key = line.split("=", 1)[0].strip()
                if key in env_updates:
                    env_lines[i] = f"{key}={env_updates[key]}\n"
                    updated_keys.add(key)

        # Append new values that weren't found
        for key, value in env_updates.items():
            if key not in updated_keys:
                env_lines.append(f"{key}={value}\n")

        # Write back to file
        with open(self.env_file, "w") as f:
            f.writelines(env_lines)


    def get_embedding_models(self) -> list:
        """Get list of recommended embedding models.

        Returns list of dicts with model info:
            - name: Model name
            - description: Brief description
            - dimensions: Embedding dimensions
            - size_mb: Approximate model size in MB
            - speed: Relative speed (fast, medium, slow)
            - quality: Relative quality (good, better, best)
        """
        return [
            {
                "name": "all-MiniLM-L6-v2",
                "description": "Default model - fast and efficient",
                "dimensions": 384,
                "size_mb": 90,
                "speed": "fast",
                "quality": "good",
                "language": "English",
            },
            {
                "name": "all-mpnet-base-v2",
                "description": "High quality - slower but more accurate",
                "dimensions": 768,
                "size_mb": 420,
                "speed": "slow",
                "quality": "best",
                "language": "English",
            },
            {
                "name": "paraphrase-MiniLM-L3-v2",
                "description": "Fastest - lower quality but very fast",
                "dimensions": 384,
                "size_mb": 60,
                "speed": "very fast",
                "quality": "fair",
                "language": "English",
            },
            {
                "name": "paraphrase-multilingual-MiniLM-L12-v2",
                "description": "Multilingual support - 50+ languages",
                "dimensions": 384,
                "size_mb": 470,
                "speed": "medium",
                "quality": "better",
                "language": "Multilingual",
            },
            {
                "name": "all-MiniLM-L12-v2",
                "description": "Balanced - good quality and speed",
                "dimensions": 384,
                "size_mb": 120,
                "speed": "medium",
                "quality": "better",
                "language": "English",
            },
        ]


# Global instance
config_manager = ConfigManager()
