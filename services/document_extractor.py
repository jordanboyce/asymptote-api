"""Generic document text extraction service supporting multiple file formats."""

from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
import logging
import io

# PDF extraction
import pdfplumber
from pypdf import PdfReader

logger = logging.getLogger(__name__)

# OCR availability flags (set during initialization)
PYTESSERACT_AVAILABLE = False
EASYOCR_AVAILABLE = False
PDF2IMAGE_AVAILABLE = False

try:
    import pytesseract
    from PIL import Image
    PYTESSERACT_AVAILABLE = True
except ImportError:
    pass

try:
    import easyocr
    EASYOCR_AVAILABLE = True
except ImportError:
    pass

try:
    from pdf2image import convert_from_path
    PDF2IMAGE_AVAILABLE = True
except ImportError:
    pass


class ExtractionResult:
    """Result of text extraction with metadata about the extraction method used."""

    def __init__(self, page_texts: Dict[int, str], method: str = "text",
                 ocr_pages: List[int] = None):
        """
        Initialize extraction result.

        Args:
            page_texts: Dictionary mapping page numbers to extracted text
            method: Extraction method used ("text", "ocr", or "hybrid")
            ocr_pages: List of page numbers where OCR was used (for hybrid)
        """
        self.page_texts = page_texts
        self.method = method
        self.ocr_pages = ocr_pages or []

    def __getitem__(self, key):
        return self.page_texts[key]

    def __iter__(self):
        return iter(self.page_texts)

    def items(self):
        return self.page_texts.items()

    def keys(self):
        return self.page_texts.keys()

    def values(self):
        return self.page_texts.values()

    def __len__(self):
        return len(self.page_texts)


class DocumentExtractor:
    """Extracts text from various document formats (PDF, TXT, DOCX, CSV, MD, JSON)."""

    SUPPORTED_EXTENSIONS = {'.pdf', '.txt', '.docx', '.csv', '.md', '.json'}

    def __init__(self, enable_ocr: bool = False, ocr_engine: str = "pytesseract",
                 ocr_language: str = "eng", ocr_fallback_only: bool = True):
        """
        Initialize the document extractor.

        Args:
            enable_ocr: Whether to enable OCR for scanned PDFs
            ocr_engine: OCR engine to use ("pytesseract" or "easyocr")
            ocr_language: Language code for OCR (e.g., "eng", "eng+fra")
            ocr_fallback_only: Only use OCR when text extraction fails/empty
        """
        self.enable_ocr = enable_ocr
        self.ocr_engine = ocr_engine
        self.ocr_language = ocr_language
        self.ocr_fallback_only = ocr_fallback_only
        self._easyocr_reader = None

        if enable_ocr:
            self._validate_ocr_setup()

    def _validate_ocr_setup(self):
        """Validate OCR dependencies are available."""
        if not PDF2IMAGE_AVAILABLE:
            logger.warning(
                "OCR enabled but pdf2image not installed. "
                "Install with: pip install pdf2image"
            )
            return

        if self.ocr_engine == "pytesseract" and not PYTESSERACT_AVAILABLE:
            logger.warning(
                "pytesseract OCR engine selected but not installed. "
                "Install with: pip install pytesseract pillow"
            )
        elif self.ocr_engine == "easyocr" and not EASYOCR_AVAILABLE:
            logger.warning(
                "easyocr OCR engine selected but not installed. "
                "Install with: pip install easyocr"
            )

    def _get_easyocr_reader(self):
        """Lazily initialize EasyOCR reader."""
        if self._easyocr_reader is None and EASYOCR_AVAILABLE:
            import easyocr
            # Parse language codes (e.g., "eng+fra" -> ["en", "fr"])
            lang_map = {"eng": "en", "fra": "fr", "deu": "de", "spa": "es",
                        "ita": "it", "por": "pt", "nld": "nl", "pol": "pl",
                        "rus": "ru", "jpn": "ja", "kor": "ko", "chi_sim": "ch_sim"}
            langs = []
            for lang in self.ocr_language.split("+"):
                langs.append(lang_map.get(lang, lang))
            self._easyocr_reader = easyocr.Reader(langs, gpu=False)
        return self._easyocr_reader

    def extract_text(self, file_path: Path) -> ExtractionResult:
        """
        Extract text from a document file, returning a mapping of page/section numbers to text.

        Args:
            file_path: Path to the document file

        Returns:
            ExtractionResult with page texts and extraction method info

        Raises:
            ValueError: If file type is not supported
            Exception: If text extraction fails
        """
        file_ext = file_path.suffix.lower()

        if file_ext not in self.SUPPORTED_EXTENSIONS:
            raise ValueError(
                f"Unsupported file type: {file_ext}. "
                f"Supported types: {', '.join(self.SUPPORTED_EXTENSIONS)}"
            )

        logger.info(f"Extracting text from {file_ext} file: {file_path.name}")

        if file_ext == '.pdf':
            return self._extract_pdf(file_path)
        elif file_ext == '.txt':
            return ExtractionResult(self._extract_txt(file_path), method="text")
        elif file_ext == '.docx':
            return ExtractionResult(self._extract_docx(file_path), method="text")
        elif file_ext == '.csv':
            return ExtractionResult(self._extract_csv(file_path), method="text")
        elif file_ext == '.md':
            return ExtractionResult(self._extract_markdown(file_path), method="text")
        elif file_ext == '.json':
            return ExtractionResult(self._extract_json(file_path), method="text")
        else:
            raise ValueError(f"Unsupported file extension: {file_ext}")

    def _extract_pdf(self, pdf_path: Path) -> ExtractionResult:
        """
        Extract text from PDF file using pdfplumber with pypdf and OCR fallback.

        Returns:
            ExtractionResult with page texts and extraction method info
        """
        page_texts = {}
        ocr_pages = []
        method = "text"

        try:
            # Try pdfplumber first (better for complex layouts)
            page_texts = self._extract_pdf_with_pdfplumber(pdf_path)
        except Exception as e:
            logger.warning(f"pdfplumber failed for {pdf_path.name}: {e}. Trying pypdf...")
            try:
                # Fallback to pypdf
                page_texts = self._extract_pdf_with_pypdf(pdf_path)
            except Exception as e2:
                logger.warning(f"pypdf failed for {pdf_path.name}: {e2}")
                page_texts = {}

        # Check if we need OCR (no text extracted or mostly empty pages)
        if self.enable_ocr:
            empty_pages = [p for p, text in page_texts.items()
                          if not text or len(text.strip()) < 50]

            should_ocr = False
            if not page_texts:
                # No text extracted at all
                should_ocr = True
            elif self.ocr_fallback_only and empty_pages:
                # OCR only for empty/near-empty pages
                should_ocr = True
            elif not self.ocr_fallback_only:
                # OCR all pages (user preference)
                should_ocr = True

            if should_ocr:
                try:
                    ocr_result = self._extract_pdf_with_ocr(pdf_path, empty_pages if self.ocr_fallback_only else None)
                    if ocr_result:
                        ocr_texts, ocr_pages = ocr_result
                        # Merge OCR results with existing text
                        for page_num, ocr_text in ocr_texts.items():
                            if page_num not in page_texts or len(page_texts.get(page_num, "").strip()) < 50:
                                page_texts[page_num] = ocr_text

                        if ocr_pages:
                            method = "hybrid" if any(p not in ocr_pages for p in page_texts.keys()) else "ocr"
                except Exception as e:
                    logger.warning(f"OCR failed for {pdf_path.name}: {e}")

        if not page_texts:
            raise Exception(f"Failed to extract text from PDF {pdf_path.name}: all methods failed")

        return ExtractionResult(page_texts, method=method, ocr_pages=ocr_pages)

    def _extract_pdf_with_pdfplumber(self, pdf_path: Path) -> Dict[int, str]:
        """Extract text using pdfplumber (handles complex layouts better)."""
        page_texts = {}

        with pdfplumber.open(pdf_path) as pdf:
            for page_num, page in enumerate(pdf.pages, start=1):
                text = page.extract_text() or ""
                page_texts[page_num] = text.strip()

        return page_texts

    def _extract_pdf_with_pypdf(self, pdf_path: Path) -> Dict[int, str]:
        """Extract text using pypdf (fallback method)."""
        page_texts = {}

        reader = PdfReader(str(pdf_path))
        for page_num, page in enumerate(reader.pages, start=1):
            text = page.extract_text() or ""
            page_texts[page_num] = text.strip()

        return page_texts

    def _extract_pdf_with_ocr(self, pdf_path: Path,
                               pages_to_ocr: Optional[List[int]] = None
                               ) -> Optional[Tuple[Dict[int, str], List[int]]]:
        """
        Extract text from PDF using OCR.

        Args:
            pdf_path: Path to PDF file
            pages_to_ocr: Specific page numbers to OCR (None = all pages)

        Returns:
            Tuple of (page_texts dict, list of OCR'd page numbers) or None if OCR fails
        """
        if not PDF2IMAGE_AVAILABLE:
            logger.warning("pdf2image not available for OCR")
            return None

        if self.ocr_engine == "pytesseract" and not PYTESSERACT_AVAILABLE:
            logger.warning("pytesseract not available for OCR")
            return None

        if self.ocr_engine == "easyocr" and not EASYOCR_AVAILABLE:
            logger.warning("easyocr not available for OCR")
            return None

        logger.info(f"Running OCR on {pdf_path.name} using {self.ocr_engine}")

        try:
            from pdf2image import convert_from_path

            # Convert PDF pages to images
            images = convert_from_path(str(pdf_path), dpi=300)

            page_texts = {}
            ocr_pages = []

            for page_num, image in enumerate(images, start=1):
                # Skip pages we don't need to OCR
                if pages_to_ocr is not None and page_num not in pages_to_ocr:
                    continue

                text = self._ocr_image(image)
                if text:
                    page_texts[page_num] = text
                    ocr_pages.append(page_num)
                    logger.debug(f"OCR extracted {len(text)} chars from page {page_num}")

            return page_texts, ocr_pages

        except Exception as e:
            logger.error(f"OCR failed for {pdf_path.name}: {e}")
            return None

    def _ocr_image(self, image) -> str:
        """
        Run OCR on a single image.

        Args:
            image: PIL Image object

        Returns:
            Extracted text string
        """
        if self.ocr_engine == "pytesseract":
            import pytesseract
            text = pytesseract.image_to_string(image, lang=self.ocr_language)
            return text.strip()

        elif self.ocr_engine == "easyocr":
            import numpy as np
            reader = self._get_easyocr_reader()
            # Convert PIL Image to numpy array
            img_array = np.array(image)
            results = reader.readtext(img_array)
            # Combine all detected text
            text = " ".join([result[1] for result in results])
            return text.strip()

        return ""

    def is_ocr_available(self) -> bool:
        """Check if OCR is available with current configuration."""
        if not PDF2IMAGE_AVAILABLE:
            return False
        if self.ocr_engine == "pytesseract":
            return PYTESSERACT_AVAILABLE
        if self.ocr_engine == "easyocr":
            return EASYOCR_AVAILABLE
        return False

    def _extract_txt(self, txt_path: Path) -> Dict[int, str]:
        """
        Extract text from plain text file.

        Returns:
            Dictionary with single entry (page 1) containing all text
        """
        try:
            # Try UTF-8 first
            with open(txt_path, 'r', encoding='utf-8') as f:
                text = f.read()
        except UnicodeDecodeError:
            # Fallback to latin-1 for broader compatibility
            logger.warning(f"UTF-8 decoding failed for {txt_path.name}, trying latin-1")
            with open(txt_path, 'r', encoding='latin-1') as f:
                text = f.read()

        # Return as single "page"
        return {1: text.strip()}

    def _extract_docx(self, docx_path: Path) -> Dict[int, str]:
        """
        Extract text from DOCX file.

        Returns:
            Dictionary mapping page numbers to text (pages are estimated by paragraphs)
        """
        try:
            from docx import Document
        except ImportError:
            raise ImportError(
                "python-docx is required for DOCX support. "
                "Install it with: pip install python-docx"
            )

        doc = Document(str(docx_path))

        # Extract all paragraphs
        paragraphs = [para.text for para in doc.paragraphs if para.text.strip()]

        if not paragraphs:
            logger.warning(f"No text found in {docx_path.name}")
            return {1: ""}

        # Group paragraphs into "pages" (every ~10 paragraphs = 1 page)
        # This is a rough approximation since DOCX doesn't have explicit pages
        paragraphs_per_page = 10
        page_texts = {}

        for i in range(0, len(paragraphs), paragraphs_per_page):
            page_num = (i // paragraphs_per_page) + 1
            page_content = '\n\n'.join(paragraphs[i:i + paragraphs_per_page])
            page_texts[page_num] = page_content.strip()

        return page_texts

    def _extract_csv(self, csv_path: Path) -> Dict[int, str]:
        """
        Extract text from CSV file (legacy format for backward compatibility).

        Returns:
            Dictionary with sections (every ~50 rows = 1 section) containing formatted text
        """
        try:
            import pandas as pd
        except ImportError:
            raise ImportError(
                "pandas is required for CSV support. "
                "Install it with: pip install pandas"
            )

        # Read CSV
        try:
            df = pd.read_csv(csv_path)
        except Exception as e:
            logger.error(f"Failed to read CSV {csv_path.name}: {e}")
            raise Exception(f"Failed to read CSV file: {e}")

        if df.empty:
            logger.warning(f"Empty CSV file: {csv_path.name}")
            return {1: ""}

        # Convert DataFrame to text representation
        # Group rows into "pages" (every 50 rows = 1 page)
        rows_per_page = 50
        page_texts = {}

        for start_idx in range(0, len(df), rows_per_page):
            page_num = (start_idx // rows_per_page) + 1
            end_idx = min(start_idx + rows_per_page, len(df))

            # Get chunk of dataframe
            df_chunk = df.iloc[start_idx:end_idx]

            # Convert to text with column headers
            lines = []

            # Add header row for first page
            if page_num == 1:
                header = " | ".join(str(col) for col in df.columns)
                lines.append(header)
                lines.append("-" * len(header))

            # Add data rows
            for _, row in df_chunk.iterrows():
                row_text = " | ".join(str(val) for val in row.values)
                lines.append(row_text)

            page_texts[page_num] = "\n".join(lines)

        return page_texts

    def extract_csv_rows(self, csv_path: Path) -> List[Dict[str, Any]]:
        """
        Extract CSV file as individual rows with column metadata (v3.0 row-level indexing).

        Args:
            csv_path: Path to CSV file

        Returns:
            List of dictionaries, each containing:
                - row_number: Original row number (1-indexed, excluding header)
                - columns: List of column names
                - values: Dictionary of column name -> value
                - text: Formatted text representation for embedding
        """
        try:
            import pandas as pd
        except ImportError:
            raise ImportError(
                "pandas is required for CSV support. "
                "Install it with: pip install pandas"
            )

        # Read CSV
        try:
            df = pd.read_csv(csv_path)
        except Exception as e:
            logger.error(f"Failed to read CSV {csv_path.name}: {e}")
            raise Exception(f"Failed to read CSV file: {e}")

        if df.empty:
            logger.warning(f"Empty CSV file: {csv_path.name}")
            return []

        columns = [str(col) for col in df.columns]
        rows = []

        for idx, (_, row) in enumerate(df.iterrows(), start=1):
            # Create a dictionary of column -> value
            values = {}
            text_parts = []

            for col in columns:
                val = row[col]
                # Handle NaN values
                if pd.isna(val):
                    val = ""
                else:
                    val = str(val)
                values[col] = val
                # Include column name in text for better semantic understanding
                text_parts.append(f"{col}: {val}")

            rows.append({
                "row_number": idx,
                "columns": columns,
                "values": values,
                "text": " | ".join(text_parts)
            })

        logger.info(f"Extracted {len(rows)} rows from CSV {csv_path.name}")
        return rows

    def _extract_markdown(self, md_path: Path) -> Dict[int, str]:
        """
        Extract text from Markdown file, chunking by headers.

        Returns:
            Dictionary mapping section numbers to text (split on h1/h2 headers)
        """
        import re

        try:
            with open(md_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except UnicodeDecodeError:
            logger.warning(f"UTF-8 decoding failed for {md_path.name}, trying latin-1")
            with open(md_path, 'r', encoding='latin-1') as f:
                content = f.read()

        if not content.strip():
            logger.warning(f"Empty markdown file: {md_path.name}")
            return {1: ""}

        # Split on h1 (# ) or h2 (## ) headers
        # Keep the header with the section
        header_pattern = r'(?=^#{1,2}\s+)'
        sections = re.split(header_pattern, content, flags=re.MULTILINE)

        # Filter out empty sections
        sections = [s.strip() for s in sections if s.strip()]

        if not sections:
            return {1: content.strip()}

        page_texts = {}
        for i, section in enumerate(sections, start=1):
            page_texts[i] = section

        return page_texts

    def _extract_json(self, json_path: Path) -> Dict[int, str]:
        """
        Extract text from JSON file.

        Returns:
            Dictionary with sections based on top-level keys or array items
        """
        import json

        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except UnicodeDecodeError:
            logger.warning(f"UTF-8 decoding failed for {json_path.name}, trying latin-1")
            with open(json_path, 'r', encoding='latin-1') as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in {json_path.name}: {e}")
            raise Exception(f"Failed to parse JSON file: {e}")

        page_texts = {}

        if isinstance(data, dict):
            # For objects, each top-level key becomes a section
            if not data:
                return {1: "{}"}

            for i, (key, value) in enumerate(data.items(), start=1):
                # Format as "key: value" for better semantic search
                value_str = json.dumps(value, indent=2) if isinstance(value, (dict, list)) else str(value)
                page_texts[i] = f"{key}: {value_str}"

        elif isinstance(data, list):
            # For arrays, chunk items (10 items per section)
            if not data:
                return {1: "[]"}

            items_per_page = 10
            for start_idx in range(0, len(data), items_per_page):
                page_num = (start_idx // items_per_page) + 1
                end_idx = min(start_idx + items_per_page, len(data))
                chunk = data[start_idx:end_idx]

                # Format each item
                lines = []
                for j, item in enumerate(chunk, start=start_idx):
                    item_str = json.dumps(item, indent=2) if isinstance(item, (dict, list)) else str(item)
                    lines.append(f"[{j}]: {item_str}")

                page_texts[page_num] = "\n\n".join(lines)
        else:
            # Primitive value
            page_texts[1] = str(data)

        return page_texts

    def get_page_count(self, file_path: Path) -> int:
        """
        Get the number of pages/sections in a document.

        Args:
            file_path: Path to the document file

        Returns:
            Number of pages/sections
        """
        try:
            page_texts = self.extract_text(file_path)
            return len(page_texts)
        except Exception as e:
            logger.error(f"Failed to get page count for {file_path.name}: {e}")
            return 0
