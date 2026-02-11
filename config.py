"""Configuration management for Asymptote API."""

from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables or .env file."""

    # Data storage
    data_dir: Path = Path("./data")

    # Embedding configuration
    embedding_model: str = "all-MiniLM-L6-v2"

    # Text chunking configuration
    chunk_size: int = 600
    chunk_overlap: int = 100

    # Search configuration
    default_top_k: int = 10
    max_top_k: int = 50

    # Metadata storage
    metadata_storage: str = "json"  # "json" or "sqlite"

    # Server configuration
    host: str = "0.0.0.0"
    port: int = 8000

    # Multi-user mode (simple browser-based user isolation)
    enable_multi_user: bool = False  # Set to True for per-user data isolation

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Ensure data directories exist
        self.data_dir.mkdir(parents=True, exist_ok=True)
        (self.data_dir / "pdfs").mkdir(exist_ok=True)
        (self.data_dir / "indexes").mkdir(exist_ok=True)


# Global settings instance
settings = Settings()
