"""Pydantic schemas for API request/response models."""

from typing import List, Optional
from pydantic import BaseModel, Field


class ChunkMetadata(BaseModel):
    """Metadata for a single text chunk."""

    chunk_id: str = Field(..., description="Unique identifier for the chunk")
    document_id: str = Field(..., description="Parent document identifier")
    filename: str = Field(..., description="Original PDF filename")
    page_number: int = Field(..., description="Page number in the PDF (1-indexed)")
    chunk_index: int = Field(..., description="Index of chunk within the page")
    text: str = Field(..., description="Chunk text content")


class DocumentMetadata(BaseModel):
    """Metadata for an indexed document."""

    document_id: str = Field(..., description="Unique identifier for the document")
    filename: str = Field(..., description="Original filename")
    total_pages: int = Field(..., description="Total number of pages")
    total_chunks: int = Field(..., description="Total number of chunks created")
    indexed_at: str = Field(default="", description="ISO timestamp of indexing")


class SearchResult(BaseModel):
    """A single search result."""

    filename: str = Field(..., description="PDF filename")
    page_number: int = Field(..., description="Page number (1-indexed)")
    text_snippet: str = Field(..., description="Matching text chunk")
    similarity_score: float = Field(..., description="Cosine similarity score (0-1)")
    document_id: str = Field(..., description="Document identifier")
    chunk_id: str = Field(..., description="Chunk identifier")
    pdf_url: str = Field(..., description="URL to download the PDF")
    page_url: str = Field(..., description="URL to view the specific page")


class UploadResponse(BaseModel):
    """Response from document upload endpoint."""

    message: str = Field(..., description="Status message")
    documents_processed: int = Field(..., description="Number of documents processed")
    total_pages: int = Field(..., description="Total pages across all documents")
    total_chunks: int = Field(..., description="Total chunks created")
    document_ids: List[str] = Field(..., description="List of created document IDs")


class AIOptions(BaseModel):
    """Optional AI enhancement settings for search."""

    enhance_query: bool = Field(False, description="Expand query with synonyms and related terms")
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
    query_enhancement: Optional[AIUsageDetail] = None
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
    enhanced_query: Optional[str] = Field(None, description="AI-expanded query (if enhancement was used)")
    ai_usage: Optional[AIUsage] = Field(None, description="AI token usage for cost transparency")


class DocumentListResponse(BaseModel):
    """Response from document list endpoint."""

    documents: List[DocumentMetadata] = Field(..., description="List of indexed documents")
    total_documents: int = Field(..., description="Total number of documents")
