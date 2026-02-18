"""Configuration management for Asymptote API."""

from pathlib import Path
from typing import Literal
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables or .env file."""

    # Data storage
    data_dir: Path = Path("./data")

    # Embedding configuration
    embedding_model: str = "all-MiniLM-L6-v2"

    # Text chunking configuration
    chunk_size: int = 550
    chunk_overlap: int = 100

    # Search configuration
    default_top_k: int = 10
    max_top_k: int = 50


    # Server configuration
    host: str = "0.0.0.0"
    port: int = 8000

    # Multi-user mode (simple browser-based user isolation)
    enable_multi_user: bool = False  # Set to True for per-user data isolation

    # v3.0: OCR configuration
    enable_ocr: bool = False  # Enable OCR for scanned PDFs
    ocr_engine: Literal["pytesseract", "easyocr"] = "pytesseract"
    ocr_language: str = "eng"  # Tesseract language code(s), e.g., "eng+fra"
    ocr_fallback_only: bool = True  # Only use OCR when text extraction fails/empty

    # v3.0: CSV indexing configuration
    csv_row_level_indexing: bool = True  # Index CSV rows individually
    csv_rows_per_chunk: int = 5  # Number of rows per chunk when not row-level

    # v3.0: Schema version (for data persistence)
    schema_version: str = "3.0"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Ensure data directories exist
        self.data_dir.mkdir(parents=True, exist_ok=True)
        (self.data_dir / "documents").mkdir(exist_ok=True)
        (self.data_dir / "indexes").mkdir(exist_ok=True)
        (self.data_dir / "backups").mkdir(exist_ok=True)  # v3.0: Backup directory


# Global settings instance
settings = Settings()
