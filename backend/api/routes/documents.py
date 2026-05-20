"""
Document Management Routes
──────────────────────────
Handles PDF upload, listing, retrieval, and deletion.

Endpoints:
    POST   /api/upload              — Upload and ingest a PDF
    GET    /api/documents           — List all documents
    GET    /api/documents/{id}      — Get document metadata
    DELETE /api/documents/{id}      — Delete document + vectors
"""

import shutil
from pathlib import Path

from fastapi import APIRouter, File, UploadFile, Form, HTTPException, status
from loguru import logger

from config import settings
from services.document_service import DocumentService
from models.schemas import (
    DocumentUploadResponse,
    DocumentListResponse,
    ErrorResponse,
)

router = APIRouter()

# Singleton service instance
_doc_service = DocumentService()

# Allowed file types
ALLOWED_EXTENSIONS = {".pdf"}


@router.post(
    "/upload",
    response_model=DocumentUploadResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"model": ErrorResponse},
        413: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
async def upload_document(
    file: UploadFile = File(...),
    document_type: str = Form("General")
):
    """
    Upload a PDF file and run the full ingestion pipeline.

    Pipeline: Upload → Extract → Clean → Chunk → Embed → Store in ChromaDB

    Returns document metadata with chunk count, pages, etc.
    """
    # ── Validate file type ────────────────────────────────
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No filename provided.",
        )

    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file type '{file_ext}'. Only PDF files are supported.",
        )

    # ── Validate file size ────────────────────────────────
    # Read file content to check size
    content = await file.read()
    file_size = len(content)

    if file_size == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty.",
        )

    if file_size > settings.max_file_size_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large ({file_size:,} bytes). Maximum: {settings.max_file_size_mb} MB.",
        )

    # ── Save to disk ──────────────────────────────────────
    upload_dir = settings.upload_path
    save_path = upload_dir / file.filename

    # Handle duplicate filenames
    counter = 1
    original_stem = save_path.stem
    while save_path.exists():
        save_path = upload_dir / f"{original_stem}_{counter}{file_ext}"
        counter += 1

    try:
        with open(save_path, "wb") as f:
            f.write(content)
        logger.info(f"Saved upload: {save_path} ({file_size:,} bytes)")
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save file: {e}",
        )

    # ── Run ingestion pipeline ────────────────────────────
    try:
        doc_meta = await _doc_service.ingest_document(
            file_path=save_path,
            original_filename=file.filename,
            document_type=document_type,
        )

        return DocumentUploadResponse(
            status="success",
            message=f"Document '{file.filename}' ingested successfully. "
                    f"{doc_meta.total_chunks} chunks created from {doc_meta.total_pages} pages.",
            document=doc_meta,
        )

    except Exception as e:
        # Clean up the saved file on failure
        if save_path.exists():
            save_path.unlink()
        logger.error(f"Ingestion failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Document ingestion failed: {str(e)}",
        )


@router.get(
    "/documents",
    response_model=DocumentListResponse,
)
async def list_documents():
    """List all ingested documents with their metadata."""
    docs = _doc_service.list_documents()

    return DocumentListResponse(
        total_documents=len(docs),
        documents=docs,
    )


@router.get(
    "/documents/{document_id}",
    responses={404: {"model": ErrorResponse}},
)
async def get_document(document_id: str):
    """Get metadata for a specific document."""
    doc = _doc_service.get_document(document_id)

    if doc is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document not found: {document_id}",
        )

    return doc


@router.delete(
    "/documents/{document_id}",
    responses={404: {"model": ErrorResponse}},
)
async def delete_document(document_id: str):
    """
    Delete a document and all its chunks from the vector store.

    This permanently removes:
    - Document metadata
    - All text chunks
    - All embeddings from ChromaDB
    """
    success = _doc_service.delete_document(document_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document not found: {document_id}",
        )

    return {
        "status": "success",
        "message": f"Document {document_id} and all associated data deleted.",
    }
