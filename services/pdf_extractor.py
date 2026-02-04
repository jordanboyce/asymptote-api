"""PDF text extraction service."""

from pathlib import Path
from typing import Dict, List
import logging

import pdfplumber
from pypdf import PdfReader

logger = logging.getLogger(__name__)


class PDFExtractor:
    """Extracts text from PDF files with fallback strategies."""

    def extract_text(self, pdf_path: Path) -> Dict[int, str]:
        """
        Extract text from a PDF file, returning a mapping of page numbers to text.

        Args:
            pdf_path: Path to the PDF file

        Returns:
            Dictionary mapping page numbers (1-indexed) to extracted text

        Raises:
            Exception: If PDF extraction fails
        """
        try:
            # Try pdfplumber first (better for complex layouts)
            return self._extract_with_pdfplumber(pdf_path)
        except Exception as e:
            logger.warning(f"pdfplumber failed for {pdf_path.name}: {e}. Trying pypdf...")
            try:
                # Fallback to pypdf
                return self._extract_with_pypdf(pdf_path)
            except Exception as e2:
                logger.error(f"Both extraction methods failed for {pdf_path.name}: {e2}")
                raise Exception(f"Failed to extract text from {pdf_path.name}: {e2}")

    def _extract_with_pdfplumber(self, pdf_path: Path) -> Dict[int, str]:
        """Extract text using pdfplumber (handles complex layouts better)."""
        page_texts = {}

        with pdfplumber.open(pdf_path) as pdf:
            for page_num, page in enumerate(pdf.pages, start=1):
                text = page.extract_text() or ""
                page_texts[page_num] = text.strip()

        return page_texts

    def _extract_with_pypdf(self, pdf_path: Path) -> Dict[int, str]:
        """Extract text using pypdf (fallback method)."""
        page_texts = {}

        reader = PdfReader(str(pdf_path))
        for page_num, page in enumerate(reader.pages, start=1):
            text = page.extract_text() or ""
            page_texts[page_num] = text.strip()

        return page_texts

    def get_page_count(self, pdf_path: Path) -> int:
        """
        Get the number of pages in a PDF.

        Args:
            pdf_path: Path to the PDF file

        Returns:
            Number of pages
        """
        try:
            with pdfplumber.open(pdf_path) as pdf:
                return len(pdf.pages)
        except Exception:
            reader = PdfReader(str(pdf_path))
            return len(reader.pages)
