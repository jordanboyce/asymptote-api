"""Pydantic schemas for API request/response models."""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class ChunkMetadata(BaseModel):
    """Metadata for a single text chunk."""

    chunk_id: str = Field(..., description="Unique identifier for the chunk")
    document_id: str = Field(..., description="Parent document identifier")
    filename: str = Field(..., description="Original filename")
    page_number: int = Field(..., description="Page number or section number (1-indexed)")
    chunk_index: int = Field(..., description="Index of chunk within the page")
    text: str = Field(..., description="Chunk text content")

    # v3.0: Format-aware metadata
    source_format: Optional[str] = Field(None, description="Source format: pdf, txt, docx, csv, md, json")
    extraction_method: Optional[str] = Field(None, description="Extraction method: text, ocr, hybrid")

    # v3.0: CSV-specific metadata (for row-level indexing)
    csv_row_number: Optional[int] = Field(None, description="Original row number in CSV (for CSV chunks)")
    csv_columns: Optional[List[str]] = Field(None, description="Column names for CSV row")
    csv_values: Optional[Dict[str, Any]] = Field(None, description="Column-value pairs for CSV row")


class DocumentMetadata(BaseModel):
    """Metadata for an indexed document."""

    document_id: str = Field(..., description="Unique identifier for the document")
    filename: str = Field(..., description="Original filename")
    total_pages: int = Field(..., description="Total number of pages")
    total_chunks: int = Field(..., description="Total number of chunks created")
    indexed_at: str = Field(default="", description="ISO timestamp of indexing")

    # v3.0: Document-level versioning and format info
    source_format: Optional[str] = Field(None, description="Source format: pdf, txt, docx, csv, md, json")
    extraction_method: Optional[str] = Field(None, description="Primary extraction method used")
    embedding_model: Optional[str] = Field(None, description="Embedding model used for this document")
    chunk_size: Optional[int] = Field(None, description="Chunk size used during indexing")
    chunk_overlap: Optional[int] = Field(None, description="Chunk overlap used during indexing")
    schema_version: str = Field(default="3.0", description="Schema version for migration compatibility")


class SearchResult(BaseModel):
    """A single search result."""

    filename: str = Field(..., description="Document filename")
    page_number: int = Field(..., description="Page or section number (1-indexed)")
    text_snippet: str = Field(..., description="Matching text chunk")
    similarity_score: float = Field(..., description="Cosine similarity score (0-1)")
    document_id: str = Field(..., description="Document identifier")
    chunk_id: str = Field(..., description="Chunk identifier")
    pdf_url: str = Field(..., description="URL to download the document")
    page_url: str = Field(..., description="URL to view the specific page")

    # v3.0: Format-aware result metadata
    source_format: Optional[str] = Field(None, description="Source format: pdf, txt, docx, csv, md, json")
    extraction_method: Optional[str] = Field(None, description="How text was extracted: text, ocr, hybrid")

    # v3.0: CSV-specific result data (for table rendering)
    csv_row_number: Optional[int] = Field(None, description="Row number for CSV results")
    csv_columns: Optional[List[str]] = Field(None, description="Column names for CSV row")
    csv_values: Optional[Dict[str, Any]] = Field(None, description="Column-value pairs for CSV row")


class UploadResponse(BaseModel):
    """Response from document upload endpoint."""

    message: str = Field(..., description="Status message")
    documents_processed: int = Field(..., description="Number of documents processed")
    total_pages: int = Field(..., description="Total pages across all documents")
    total_chunks: int = Field(..., description="Total chunks created")
    document_ids: List[str] = Field(..., description="List of created document IDs")


class AIOptions(BaseModel):
    """Optional AI enhancement settings for search."""

    provider: str = Field("anthropic", description="AI provider: 'anthropic' or 'openai'")
    rerank: bool = Field(False, description="Rerank results using AI for better relevance")
    synthesize: bool = Field(False, description="Generate an AI summary with citations")


class SearchRequest(BaseModel):
    """Request body for search endpoint."""

    query: str = Field(..., description="Search query text", min_length=1)
    top_k: int = Field(10, description="Number of results to return", ge=1, le=50)
    ai: Optional[AIOptions] = Field(None, description="Optional AI enhancement settings")


class AIUsageDetail(BaseModel):
    """Token usage for a single AI operation."""

    input_tokens: int = Field(..., description="Input tokens consumed")
    output_tokens: int = Field(..., description="Output tokens consumed")
    model: str = Field(..., description="Model used")


class AIUsage(BaseModel):
    """AI usage metadata for cost transparency."""

    features_used: List[str] = Field(default_factory=list, description="AI features that were applied")
    reranking: Optional[AIUsageDetail] = None
    synthesis: Optional[AIUsageDetail] = None
    total_input_tokens: int = Field(0, description="Total input tokens across all AI calls")
    total_output_tokens: int = Field(0, description="Total output tokens across all AI calls")


class SearchResponse(BaseModel):
    """Response from search endpoint."""

    query: str = Field(..., description="Original search query")
    results: List[SearchResult] = Field(..., description="Ranked search results")
    total_results: int = Field(..., description="Total number of results returned")
    synthesis: Optional[str] = Field(None, description="AI-generated answer with citations")
    ai_usage: Optional[AIUsage] = Field(None, description="AI token usage for cost transparency")


class DocumentListResponse(BaseModel):
    """Response from document list endpoint."""

    documents: List[DocumentMetadata] = Field(..., description="List of indexed documents")
    total_documents: int = Field(..., description="Total number of documents")


# Agent API schemas
class AskRequest(BaseModel):
    """Request for the /api/ask endpoint optimized for coding agents."""

    question: str = Field(..., description="The question to answer", min_length=1)
    collection_id: str = Field("default", description="Collection to search")
    top_k: int = Field(5, description="Number of source chunks to consider", ge=1, le=20)
    rerank: bool = Field(True, description="Rerank results using AI before synthesis (improves answer quality)")
    include_sources: bool = Field(True, description="Include source excerpts in response")
    max_source_length: int = Field(500, description="Max characters per source excerpt", ge=100, le=2000)
    format: str = Field("markdown", description="Response format: 'text', 'markdown', or 'json'")


class AskSource(BaseModel):
    """A source used to answer the question."""

    filename: str = Field(..., description="Source document filename")
    page: int = Field(..., description="Page or section number")
    excerpt: str = Field(..., description="Relevant text excerpt")
    relevance: float = Field(..., description="Similarity score (0-1)")


class AskResponse(BaseModel):
    """Response from the /api/ask endpoint."""

    answer: str = Field(..., description="The synthesized answer to the question")
    sources: List[AskSource] = Field(default_factory=list, description="Sources used for the answer")
    collection_id: str = Field(..., description="Collection that was searched")
    model: str = Field(..., description="AI model used for synthesis")
    tokens_used: int = Field(0, description="Total tokens consumed")
