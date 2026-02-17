"""Generic document text extraction service supporting multiple file formats."""

from pathlib import Path
from typing import Dict, List
import logging

# PDF extraction
import pdfplumber
from pypdf import PdfReader

logger = logging.getLogger(__name__)


class DocumentExtractor:
    """Extracts text from various document formats (PDF, TXT, DOCX, CSV, MD, JSON)."""

    SUPPORTED_EXTENSIONS = {'.pdf', '.txt', '.docx', '.csv', '.md', '.json'}

    def extract_text(self, file_path: Path) -> Dict[int, str]:
        """
        Extract text from a document file, returning a mapping of page/section numbers to text.

        Args:
            file_path: Path to the document file

        Returns:
            Dictionary mapping page/section numbers (1-indexed) to extracted text

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
            return self._extract_txt(file_path)
        elif file_ext == '.docx':
            return self._extract_docx(file_path)
        elif file_ext == '.csv':
            return self._extract_csv(file_path)
        elif file_ext == '.md':
            return self._extract_markdown(file_path)
        elif file_ext == '.json':
            return self._extract_json(file_path)
        else:
            raise ValueError(f"Unsupported file extension: {file_ext}")

    def _extract_pdf(self, pdf_path: Path) -> Dict[int, str]:
        """
        Extract text from PDF file using pdfplumber with pypdf fallback.

        Returns:
            Dictionary mapping page numbers (1-indexed) to text
        """
        try:
            # Try pdfplumber first (better for complex layouts)
            return self._extract_pdf_with_pdfplumber(pdf_path)
        except Exception as e:
            logger.warning(f"pdfplumber failed for {pdf_path.name}: {e}. Trying pypdf...")
            try:
                # Fallback to pypdf
                return self._extract_pdf_with_pypdf(pdf_path)
            except Exception as e2:
                logger.error(f"Both PDF extraction methods failed for {pdf_path.name}: {e2}")
                raise Exception(f"Failed to extract text from PDF {pdf_path.name}: {e2}")

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
        Extract text from CSV file.

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
