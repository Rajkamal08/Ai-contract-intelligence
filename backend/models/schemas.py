"""
Pydantic schemas — Request/Response models for all API endpoints.
Strict typing ensures contract safety between frontend and backend.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


# ═══════════════════════════════════════════════════════════
# Document Models
# ═══════════════════════════════════════════════════════════

class DocumentMetadata(BaseModel):
    """Metadata stored alongside each document."""
    document_id: str
    filename: str
    upload_time: datetime
    total_pages: int
    total_chunks: int
    file_size_bytes: int
    document_type: str = "General"
    risk_score: Optional[int] = None


class DocumentUploadResponse(BaseModel):
    """Response after successful document upload + ingestion."""
    status: str = "success"
    message: str
    document: DocumentMetadata


class DocumentListResponse(BaseModel):
    """Response for listing all ingested documents."""
    total_documents: int
    documents: list[DocumentMetadata]


# ═══════════════════════════════════════════════════════════
# Chunk Models
# ═══════════════════════════════════════════════════════════

class ChunkMetadata(BaseModel):
    """Metadata for a single text chunk."""
    chunk_id: str
    document_id: str
    filename: str
    page_number: int
    chunk_index: int
    char_count: int


class ChunkWithScore(BaseModel):
    """A retrieved chunk with its similarity score."""
    text: str
    metadata: ChunkMetadata
    similarity_score: float


# ═══════════════════════════════════════════════════════════
# Query Models
# ═══════════════════════════════════════════════════════════

class QueryRequest(BaseModel):
    """User query input."""
    question: str = Field(..., min_length=3, max_length=2000)
    top_k: Optional[int] = Field(default=None, ge=1, le=20)
    document_id: Optional[str] = Field(
        default=None,
        description="Filter retrieval to a specific document"
    )
    document_type: Optional[str] = Field(
        default=None,
        description="Filter retrieval to a specific document type"
    )


class Citation(BaseModel):
    """A single citation reference."""
    source_file: str
    page_number: int
    chunk_index: int
    relevant_text: str
    similarity_score: float


class QueryResponse(BaseModel):
    """RAG-generated answer with citations."""
    answer: str
    citations: list[Citation]
    total_chunks_retrieved: int
    model_used: str
    confidence_note: str = ""


# ═══════════════════════════════════════════════════════════
# Structured Extraction Models
# ═══════════════════════════════════════════════════════════

class StructuredExtractionRequest(BaseModel):
    """Request for extracting specific data via One-Click Prompts."""
    prompt_type: str = Field(..., description="E.g., 'Summarize Liabilities', 'Extract Clauses', 'Risk Analysis'")
    document_id: Optional[str] = None
    document_type: Optional[str] = None

class ExtractionResponse(BaseModel):
    """JSON structured response for UI rendering."""
    title: str
    data: dict
    model_used: str


# ═══════════════════════════════════════════════════════════
# Chat History Models
# ═══════════════════════════════════════════════════════════

class ChatMessage(BaseModel):
    """A single chat exchange."""
    message_id: str
    question: str
    answer: str
    citations: list[Citation]
    timestamp: datetime


class ChatHistoryResponse(BaseModel):
    """Response for chat history endpoint."""
    total_messages: int
    messages: list[ChatMessage]


# ═══════════════════════════════════════════════════════════
# Error Models
# ═══════════════════════════════════════════════════════════

class ErrorResponse(BaseModel):
    """Standard error response."""
    status: str = "error"
    message: str
    detail: Optional[str] = None
