"""OCR Engine abstraction layer for scanned PDF processing.

This module provides a unified interface for OCR engines, allowing different
backends to be swapped without changing the document extraction pipeline.

Supported engines:
- MarkerOCREngine: Primary engine using Marker/Surya pipeline (recommended)
- DoclingOCREngine: Fallback engine using Docling/Tesseract (CPU-friendly)
- LegacyOCREngine: Basic OCR using pytesseract/easyocr (existing implementation)
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Dict, Optional, Any
import logging

logger = logging.getLogger(__name__)


@dataclass
class OCRPage:
    """Result of OCR for a single page."""
    page_number: int
    text: str
    confidence: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class OCRResult:
    """Complete OCR result for a document."""
    pages: List[OCRPage]
    engine: str
    full_text: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Compute full text from pages if not provided."""
        if not self.full_text and self.pages:
            self.full_text = "\n\n".join(p.text for p in self.pages if p.text)

    def to_page_dict(self) -> Dict[int, str]:
        """Convert to page number -> text dictionary for compatibility."""
        return {p.page_number: p.text for p in self.pages}


class OCREngine(ABC):
    """Abstract base class for OCR engines."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the engine name for logging and metadata."""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check if the engine's dependencies are installed and working."""
        pass

    @abstractmethod
    def extract_text(self, pdf_path: str) -> OCRResult:
        """
        Extract text from a PDF using OCR.

        Args:
            pdf_path: Path to the PDF file

        Returns:
            OCRResult with extracted text and metadata
        """
        pass

    def extract_text_by_page(self, pdf_path: str) -> Dict[int, str]:
        """
        Extract text from a PDF, returning a dict mapping page numbers to text.

        This is a convenience method that wraps extract_text().

        Args:
            pdf_path: Path to the PDF file

        Returns:
            Dictionary mapping page numbers (1-indexed) to extracted text
        """
        result = self.extract_text(pdf_path)
        return result.to_page_dict()


class MarkerOCREngine(OCREngine):
    """
    OCR engine using Marker/Surya pipeline.

    Marker is a full end-to-end pipeline that converts PDFs to Markdown.
    It handles layout detection, table recognition, and reading order automatically.

    Requirements:
        pip install marker-pdf

    Hardware:
        - GPU recommended but not required
        - ~2-4GB VRAM usage
    """

    def __init__(self, output_format: str = "markdown"):
        """
        Initialize the Marker OCR engine.

        Args:
            output_format: Output format - "markdown", "json", or "html"
        """
        self.output_format = output_format
        self._converter = None

    @property
    def name(self) -> str:
        return "marker"

    def is_available(self) -> bool:
        """Check if Marker is installed and working."""
        try:
            from marker.converters.pdf import PdfConverter
            return True
        except ImportError:
            return False

    def _get_converter(self):
        """Lazily initialize the Marker converter."""
        if self._converter is None:
            try:
                from marker.converters.pdf import PdfConverter
                from marker.config.parser import ConfigParser

                config_parser = ConfigParser({"output_format": self.output_format})
                self._converter = PdfConverter(config=config_parser.generate_config_dict())
                logger.info("Marker OCR engine initialized")
            except Exception as e:
                logger.error(f"Failed to initialize Marker: {e}")
                raise
        return self._converter

    def extract_text(self, pdf_path: str) -> OCRResult:
        """Extract text from PDF using Marker."""
        logger.info(f"Running Marker OCR on {pdf_path}")

        converter = self._get_converter()
        rendered = converter(pdf_path)

        # Marker returns a rendered document object
        # The markdown attribute contains the full text
        full_text = rendered.markdown if hasattr(rendered, 'markdown') else str(rendered)

        # Marker doesn't provide per-page results in the simple API,
        # so we return the full document as a single page
        # For more granular results, we could use the lower-level API
        pages = [OCRPage(
            page_number=1,
            text=full_text,
            metadata={"format": self.output_format}
        )]

        return OCRResult(
            pages=pages,
            engine=self.name,
            full_text=full_text,
            metadata={
                "output_format": self.output_format,
                "source_file": pdf_path
            }
        )


class DoclingOCREngine(OCREngine):
    """
    OCR engine using IBM's Docling toolkit.

    Docling provides document conversion with layout analysis and
    falls back to Tesseract/EasyOCR for scanned pages. It's MIT licensed
    and runs well on CPU.

    Requirements:
        pip install docling

    Hardware:
        - CPU-friendly, no GPU required
        - Good for air-gapped/local execution
    """

    def __init__(self):
        """Initialize the Docling OCR engine."""
        self._converter = None

    @property
    def name(self) -> str:
        return "docling"

    def is_available(self) -> bool:
        """Check if Docling is installed."""
        try:
            from docling.document_converter import DocumentConverter
            return True
        except ImportError:
            return False

    def _get_converter(self):
        """Lazily initialize the Docling converter."""
        if self._converter is None:
            try:
                from docling.document_converter import DocumentConverter
                self._converter = DocumentConverter()
                logger.info("Docling OCR engine initialized")
            except Exception as e:
                logger.error(f"Failed to initialize Docling: {e}")
                raise
        return self._converter

    def extract_text(self, pdf_path: str) -> OCRResult:
        """Extract text from PDF using Docling."""
        logger.info(f"Running Docling OCR on {pdf_path}")

        converter = self._get_converter()
        result = converter.convert(pdf_path)

        # Export to markdown
        markdown = result.document.export_to_markdown()

        pages = [OCRPage(
            page_number=1,
            text=markdown,
            metadata={"format": "markdown"}
        )]

        return OCRResult(
            pages=pages,
            engine=self.name,
            full_text=markdown,
            metadata={
                "source_file": pdf_path
            }
        )


class LegacyOCREngine(OCREngine):
    """
    Legacy OCR engine using pytesseract or easyocr.

    This wraps the existing OCR implementation in the document_extractor module
    for backward compatibility. It's simpler than the VLM-based engines but
    less accurate on complex layouts.

    Requirements:
        pip install pytesseract pillow pdf2image
        # OR
        pip install easyocr pdf2image

    Also requires Tesseract to be installed on the system for pytesseract.
    """

    def __init__(self, engine: str = "pytesseract", language: str = "eng"):
        """
        Initialize the legacy OCR engine.

        Args:
            engine: OCR backend - "pytesseract" or "easyocr"
            language: Tesseract language code (e.g., "eng", "eng+fra")
        """
        self._engine = engine
        self._language = language
        self._easyocr_reader = None

    @property
    def name(self) -> str:
        return f"legacy_{self._engine}"

    def is_available(self) -> bool:
        """Check if the selected engine is available."""
        try:
            from pdf2image import convert_from_path

            if self._engine == "pytesseract":
                import pytesseract
                return True
            elif self._engine == "easyocr":
                import easyocr
                return True
            return False
        except ImportError:
            return False

    def _get_easyocr_reader(self):
        """Lazily initialize EasyOCR reader."""
        if self._easyocr_reader is None:
            import easyocr

            # Map Tesseract language codes to EasyOCR codes
            lang_map = {
                "eng": "en", "fra": "fr", "deu": "de", "spa": "es",
                "ita": "it", "por": "pt", "nld": "nl", "pol": "pl",
                "rus": "ru", "jpn": "ja", "kor": "ko", "chi_sim": "ch_sim"
            }
            langs = []
            for lang in self._language.split("+"):
                langs.append(lang_map.get(lang, lang))

            self._easyocr_reader = easyocr.Reader(langs, gpu=False)
        return self._easyocr_reader

    def extract_text(self, pdf_path: str) -> OCRResult:
        """Extract text from PDF using pytesseract or easyocr."""
        logger.info(f"Running legacy OCR ({self._engine}) on {pdf_path}")

        from pdf2image import convert_from_path
        import numpy as np

        # Convert PDF pages to images
        images = convert_from_path(str(pdf_path), dpi=300)

        pages = []
        for page_num, image in enumerate(images, start=1):
            text = ""

            if self._engine == "pytesseract":
                import pytesseract
                text = pytesseract.image_to_string(image, lang=self._language)
            elif self._engine == "easyocr":
                reader = self._get_easyocr_reader()
                img_array = np.array(image)
                results = reader.readtext(img_array)
                text = " ".join([r[1] for r in results])

            pages.append(OCRPage(
                page_number=page_num,
                text=text.strip(),
                metadata={"engine": self._engine}
            ))
            logger.debug(f"OCR extracted {len(text)} chars from page {page_num}")

        return OCRResult(
            pages=pages,
            engine=self.name,
            metadata={
                "language": self._language,
                "source_file": pdf_path
            }
        )


def get_available_engines() -> List[str]:
    """Get list of available OCR engines."""
    engines = []

    # Check Marker
    try:
        from marker.converters.pdf import PdfConverter
        engines.append("marker")
    except ImportError:
        pass

    # Check Docling
    try:
        from docling.document_converter import DocumentConverter
        engines.append("docling")
    except ImportError:
        pass

    # Check legacy engines
    try:
        from pdf2image import convert_from_path
        try:
            import pytesseract
            engines.append("pytesseract")
        except ImportError:
            pass
        try:
            import easyocr
            engines.append("easyocr")
        except ImportError:
            pass
    except ImportError:
        pass

    return engines


def create_ocr_engine(
    engine_name: str = "auto",
    fallback: bool = True,
    **kwargs
) -> Optional[OCREngine]:
    """
    Create an OCR engine instance.

    Args:
        engine_name: Engine to use - "marker", "docling", "pytesseract",
                     "easyocr", or "auto" (selects best available)
        fallback: If True and the requested engine isn't available,
                  try to use a fallback engine
        **kwargs: Additional arguments passed to the engine constructor

    Returns:
        OCREngine instance, or None if no engine is available
    """
    available = get_available_engines()

    if not available:
        logger.warning("No OCR engines available. Install marker-pdf, docling, or pytesseract.")
        return None

    # Auto-select best available engine
    if engine_name == "auto":
        # Preference order: marker > docling > pytesseract > easyocr
        for preferred in ["marker", "docling", "pytesseract", "easyocr"]:
            if preferred in available:
                engine_name = preferred
                break

    # Create the requested engine
    if engine_name == "marker" and "marker" in available:
        return MarkerOCREngine(**kwargs)
    elif engine_name == "docling" and "docling" in available:
        return DoclingOCREngine()
    elif engine_name == "pytesseract" and "pytesseract" in available:
        return LegacyOCREngine(engine="pytesseract", **kwargs)
    elif engine_name == "easyocr" and "easyocr" in available:
        return LegacyOCREngine(engine="easyocr", **kwargs)

    # Fallback if requested engine not available
    if fallback and available:
        logger.warning(f"Requested OCR engine '{engine_name}' not available, falling back to '{available[0]}'")
        return create_ocr_engine(available[0], fallback=False, **kwargs)

    logger.error(f"OCR engine '{engine_name}' not available")
    return None


def is_scanned_pdf(pdf_path: str, threshold: int = 100) -> bool:
    """
    Check if a PDF is likely scanned (image-only) by attempting text extraction.

    Args:
        pdf_path: Path to the PDF file
        threshold: Minimum average characters per page to consider as text-based

    Returns:
        True if the PDF appears to be scanned/image-only
    """
    import pdfplumber

    try:
        with pdfplumber.open(pdf_path) as pdf:
            if not pdf.pages:
                return False

            total_chars = 0
            for page in pdf.pages:
                text = page.extract_text() or ""
                total_chars += len(text.strip())

            avg_chars_per_page = total_chars / len(pdf.pages)
            is_scanned = avg_chars_per_page < threshold

            if is_scanned:
                logger.info(
                    f"PDF '{pdf_path}' detected as scanned "
                    f"({avg_chars_per_page:.0f} avg chars/page < {threshold} threshold)"
                )

            return is_scanned

    except Exception as e:
        logger.warning(f"Error checking if PDF is scanned: {e}")
        return False
