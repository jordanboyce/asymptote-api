"""Text chunking service for splitting documents into searchable chunks."""

from typing import List, Dict, Any, Optional
import logging

from models.schemas import ChunkMetadata

logger = logging.getLogger(__name__)


class TextChunker:
    """Splits text into overlapping chunks suitable for embedding."""

    def __init__(self, chunk_size: int = 600, chunk_overlap: int = 100):
        """
        Initialize the text chunker.

        Args:
            chunk_size: Target size of each chunk in characters
            chunk_overlap: Number of characters to overlap between chunks
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

        if chunk_overlap >= chunk_size:
            raise ValueError("chunk_overlap must be less than chunk_size")

    def chunk_document(
        self,
        page_texts: dict[int, str],
        document_id: str,
        filename: str,
        source_format: Optional[str] = None,
        extraction_method: Optional[str] = None,
    ) -> List[ChunkMetadata]:
        """
        Split a document's pages into overlapping chunks.

        Args:
            page_texts: Dictionary mapping page numbers to text content
            document_id: Unique identifier for the document
            filename: Original filename
            source_format: Source file format (pdf, txt, etc.)
            extraction_method: How text was extracted (text, ocr, hybrid)

        Returns:
            List of ChunkMetadata objects
        """
        all_chunks = []

        for page_num, text in page_texts.items():
            if not text.strip():
                logger.debug(f"Skipping empty page {page_num} in {filename}")
                continue

            page_chunks = self._chunk_text(text)

            for chunk_idx, chunk_text in enumerate(page_chunks):
                chunk_id = f"{document_id}_p{page_num}_c{chunk_idx}"

                chunk_metadata = ChunkMetadata(
                    chunk_id=chunk_id,
                    document_id=document_id,
                    filename=filename,
                    page_number=page_num,
                    chunk_index=chunk_idx,
                    text=chunk_text,
                    source_format=source_format,
                    extraction_method=extraction_method,
                )
                all_chunks.append(chunk_metadata)

        return all_chunks

    def chunk_csv_rows(
        self,
        csv_rows: List[Dict[str, Any]],
        document_id: str,
        filename: str,
        rows_per_chunk: int = 1,
    ) -> List[ChunkMetadata]:
        """
        Create chunks from CSV rows with column metadata (v3.0 row-level indexing).

        Args:
            csv_rows: List of row dictionaries from extract_csv_rows()
            document_id: Unique identifier for the document
            filename: Original filename
            rows_per_chunk: Number of rows per chunk (1 for row-level indexing)

        Returns:
            List of ChunkMetadata objects with CSV-specific metadata
        """
        all_chunks = []

        if rows_per_chunk == 1:
            # Row-level indexing: each row is its own chunk
            for row_data in csv_rows:
                row_num = row_data["row_number"]
                chunk_id = f"{document_id}_r{row_num}"

                chunk_metadata = ChunkMetadata(
                    chunk_id=chunk_id,
                    document_id=document_id,
                    filename=filename,
                    page_number=row_num,  # Use row number as "page"
                    chunk_index=0,
                    text=row_data["text"],
                    source_format="csv",
                    extraction_method="text",
                    csv_row_number=row_num,
                    csv_columns=row_data["columns"],
                    csv_values=row_data["values"],
                )
                all_chunks.append(chunk_metadata)
        else:
            # Group rows into chunks
            for i in range(0, len(csv_rows), rows_per_chunk):
                chunk_rows = csv_rows[i:i + rows_per_chunk]
                chunk_num = (i // rows_per_chunk) + 1
                chunk_id = f"{document_id}_chunk{chunk_num}"

                # Combine row texts
                combined_text = "\n".join(r["text"] for r in chunk_rows)

                # Use first row's columns (they should all be the same)
                columns = chunk_rows[0]["columns"] if chunk_rows else []

                # For multi-row chunks, store first row number and values list
                first_row_num = chunk_rows[0]["row_number"] if chunk_rows else 1

                chunk_metadata = ChunkMetadata(
                    chunk_id=chunk_id,
                    document_id=document_id,
                    filename=filename,
                    page_number=chunk_num,
                    chunk_index=0,
                    text=combined_text,
                    source_format="csv",
                    extraction_method="text",
                    csv_row_number=first_row_num,
                    csv_columns=columns,
                    # For multi-row chunks, values contains the first row's values
                    csv_values=chunk_rows[0]["values"] if len(chunk_rows) == 1 else None,
                )
                all_chunks.append(chunk_metadata)

        logger.info(f"Created {len(all_chunks)} chunks from {len(csv_rows)} CSV rows")
        return all_chunks

    def _chunk_text(self, text: str) -> List[str]:
        """
        Split a single text into overlapping chunks.

        Args:
            text: Text to split

        Returns:
            List of text chunks
        """
        if len(text) <= self.chunk_size:
            return [text]

        chunks = []
        start = 0

        while start < len(text):
            # Calculate end position
            end = start + self.chunk_size

            # If this is not the last chunk, try to break at a sentence or word boundary
            if end < len(text):
                # Look for sentence boundaries (. ! ?) within the last 20% of the chunk
                boundary_search_start = end - int(self.chunk_size * 0.2)
                chunk_preview = text[boundary_search_start:end]

                # Try to find sentence boundary
                for delimiter in [". ", "! ", "? ", "\n\n", "\n"]:
                    last_delimiter = chunk_preview.rfind(delimiter)
                    if last_delimiter != -1:
                        end = boundary_search_start + last_delimiter + len(delimiter)
                        break
                else:
                    # No sentence boundary found, try word boundary
                    last_space = chunk_preview.rfind(" ")
                    if last_space != -1:
                        end = boundary_search_start + last_space + 1

            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)

            # Move start position, accounting for overlap
            start = end - self.chunk_overlap

            # Prevent infinite loop if overlap is too large or negative
            if start < 0:
                start = 0

            # Ensure we're making progress
            if len(chunks) > 0 and start <= end - self.chunk_size:
                # If we're not making progress, just move forward
                start = end

        return chunks
