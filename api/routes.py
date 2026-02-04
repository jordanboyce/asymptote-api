"""API route handlers for Asymptote."""

from typing import List
from pathlib import Path
import logging
import shutil

from fastapi import APIRouter, UploadFile, File, HTTPException, status

from models.schemas import (
    UploadResponse,
    SearchRequest,
    SearchResponse,
    DocumentListResponse,
    DocumentMetadata,
)
from services.indexing import DocumentIndexer

logger = logging.getLogger(__name__)

router = APIRouter()


def create_routes(indexer: DocumentIndexer, data_dir: Path) -> APIRouter:
    """
    Create API routes with dependencies injected.

    Args:
        indexer: Document indexer instance
        data_dir: Data directory for storing uploaded PDFs

    Returns:
        Configured APIRouter
    """
    pdf_dir = data_dir / "pdfs"
    pdf_dir.mkdir(parents=True, exist_ok=True)

    @router.post(
        "/documents/upload",
        response_model=UploadResponse,
        status_code=status.HTTP_201_CREATED,
        summary="Upload and index PDF documents",
    )
    async def upload_documents(files: List[UploadFile] = File(...)) -> UploadResponse:
        """
        Upload one or more PDF files and automatically index their contents.

        Returns metadata about the indexed documents including page and chunk counts.
        """
        if not files:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No files provided",
            )

        # Validate all files are PDFs
        for file in files:
            if not file.filename.lower().endswith(".pdf"):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"File {file.filename} is not a PDF",
                )

        indexed_docs = []
        total_pages = 0
        total_chunks = 0

        for file in files:
            try:
                # Save uploaded file
                file_path = pdf_dir / file.filename
                with open(file_path, "wb") as f:
                    shutil.copyfileobj(file.file, f)

                logger.info(f"Saved uploaded file: {file.filename}")

                # Index the document
                doc_metadata = indexer.index_document(file_path, file.filename)

                indexed_docs.append(doc_metadata.document_id)
                total_pages += doc_metadata.num_pages
                total_chunks += doc_metadata.num_chunks

            except Exception as e:
                logger.error(f"Failed to index {file.filename}: {e}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to index {file.filename}: {str(e)}",
                )

        # Persist the index
        indexer.save_index()

        return UploadResponse(
            message=f"Successfully indexed {len(indexed_docs)} document(s)",
            documents_processed=len(indexed_docs),
            total_pages=total_pages,
            total_chunks=total_chunks,
            document_ids=indexed_docs,
        )

    @router.post(
        "/search",
        response_model=SearchResponse,
        summary="Search indexed documents",
    )
    async def search_documents(request: SearchRequest) -> SearchResponse:
        """
        Perform semantic similarity search over indexed documents.

        Returns ranked results with filename, page number, text snippet, and similarity score.
        """
        try:
            results = indexer.search(request.query, top_k=request.top_k)

            return SearchResponse(
                query=request.query,
                results=results,
                total_results=len(results),
            )

        except Exception as e:
            logger.error(f"Search failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Search failed: {str(e)}",
            )

    @router.get(
        "/documents",
        response_model=DocumentListResponse,
        summary="List all indexed documents",
    )
    async def list_documents() -> DocumentListResponse:
        """
        List all indexed documents with their metadata.

        Returns filename, page count, and chunk count for each document.
        """
        try:
            documents = indexer.list_documents()

            # Convert to DocumentMetadata objects
            doc_metadata_list = []
            for doc in documents:
                # Add placeholder timestamp (not tracked in current implementation)
                doc_metadata = DocumentMetadata(
                    document_id=doc["document_id"],
                    filename=doc["filename"],
                    num_pages=doc["num_pages"],
                    num_chunks=doc["num_chunks"],
                    upload_timestamp="",  # Not tracked in vector store
                )
                doc_metadata_list.append(doc_metadata)

            return DocumentListResponse(
                documents=doc_metadata_list,
                total_documents=len(doc_metadata_list),
            )

        except Exception as e:
            logger.error(f"Failed to list documents: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to list documents: {str(e)}",
            )

    @router.delete(
        "/documents/{document_id}",
        status_code=status.HTTP_200_OK,
        summary="Delete a document from the index",
    )
    async def delete_document(document_id: str):
        """
        Remove a document and all its chunks from the index.

        Note: Current implementation has limitations - see vector_store.py for details.
        """
        try:
            num_deleted = indexer.delete_document(document_id)

            if num_deleted == 0:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Document {document_id} not found",
                )

            # Persist the changes
            indexer.save_index()

            return {
                "message": f"Deleted document {document_id}",
                "chunks_deleted": num_deleted,
            }

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to delete document: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to delete document: {str(e)}",
            )

    return router
