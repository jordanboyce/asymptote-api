"""Configuration management for Asymptote API."""

from pathlib import Path
from typing import Literal
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables or .env file."""

    # Data storage
    data_dir: Path = Path("./data")

    # Embedding configuration
    embedding_model: str = "BAAI/bge-base-en-v1.5"

    # Text chunking configuration
    chunk_size: int = 1000
    chunk_overlap: int = 200

    # Search configuration
    default_top_k: int = 10
    max_top_k: int = 50


    # Server configuration
    host: str = "0.0.0.0"
    port: int = 8000

    # Multi-user mode (simple browser-based user isolation)
    enable_multi_user: bool = False  # Set to True for per-user data isolation

    # v3.0: OCR configuration
    # NOTE: OCR is disabled by default due to high memory requirements.
    # Docling/Marker can use 4-8GB+ RAM for large PDFs and may fail with std::bad_alloc.
    # Enable OCR only if you have sufficient system memory.
    # OCR is intended for small scanned documents (receipts, forms, letters), NOT books/manuals.
    enable_ocr: bool = False  # Enable OCR for scanned PDFs (requires extra memory)
    ocr_engine: Literal["auto", "marker", "docling", "pytesseract", "easyocr"] = "auto"
    ocr_fallback_engine: Literal["docling", "pytesseract", "easyocr"] = "pytesseract"
    ocr_language: str = "eng"  # Tesseract language code(s), e.g., "eng+fra"
    ocr_fallback_only: bool = True  # Only use OCR when text extraction fails/empty
    ocr_char_threshold: int = 100  # Min chars per page before triggering OCR
    ocr_max_pages: int = 25  # Skip OCR for PDFs with more pages than this
    ocr_max_file_mb: int = 50  # Skip OCR for files larger than this (MB)
    ocr_output_format: Literal["markdown", "text"] = "markdown"
    ocr_batch_size: int = 5  # Pages to process per batch (reduced for memory safety)
    ocr_gpu_enabled: bool = True  # Use GPU acceleration if available

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
