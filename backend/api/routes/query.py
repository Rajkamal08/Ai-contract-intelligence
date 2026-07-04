"""
Query & Chat History Routes
────────────────────────────
Handles RAG queries and chat history management.

Endpoints:
    POST   /api/query    — Ask a question (RAG pipeline)
    GET    /api/history   — Get chat history
    DELETE /api/history   — Clear chat history
"""

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, status
from loguru import logger

from config import settings
from core.rag_engine import RAGEngine
from models.schemas import (
    QueryRequest,
    QueryResponse,
    ChatMessage,
    ChatHistoryResponse,
    ErrorResponse,
    StructuredExtractionRequest,
    ExtractionResponse,
)

router = APIRouter()

# RAG engine singleton
_rag_engine = RAGEngine()

# In-memory chat history (swap for DB in production)
_chat_history: list[ChatMessage] = []


@router.post(
    "/query",
    response_model=QueryResponse,
    responses={
        400: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
async def query_documents(request: QueryRequest):
    """
    Ask a question about uploaded documents.

    The RAG pipeline:
        1. Embeds the query
        2. Retrieves top-k relevant chunks from ChromaDB
        3. Filters by similarity threshold
        4. Builds grounded context with source labels
        5. Calls Groq LLM with strict no-hallucination prompt
        6. Returns answer with citations

    Answers come ONLY from retrieved context — never hallucinated.
    """
    logger.info(f"Query received: '{request.question[:80]}...'")

    try:
        response = _rag_engine.query(
            question=request.question,
            top_k=request.top_k,
            document_id=request.document_id,
            document_type=request.document_type,
        )

        # ── Store in chat history ─────────────────────────
        chat_msg = ChatMessage(
            message_id=str(uuid.uuid4()),
            question=request.question,
            answer=response.answer,
            citations=response.citations,
            timestamp=datetime.now(timezone.utc),
        )
        _chat_history.append(chat_msg)

        logger.info(
            f"Query answered. Citations: {len(response.citations)}, "
            f"Chunks retrieved: {response.total_chunks_retrieved}"
        )

        return response

    except RuntimeError as e:
        # Groq API key missing or LLM call failed
        error_msg = str(e)
        logger.error(f"RAG query failed: {error_msg}")

        if "GROQ_API_KEY" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Groq API key is not configured. Set GROQ_API_KEY in your .env file.",
            )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Query processing failed: {error_msg}",
        )

    except Exception as e:
        logger.error(f"Unexpected error during query: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(e)}",
        )


@router.post(
    "/extract",
    response_model=ExtractionResponse,
    responses={
        500: {"model": ErrorResponse},
    },
)
async def extract_structured_data(request: StructuredExtractionRequest):
    """
    Perform a structured data extraction using One-Click Prompts.
    """
    try:
        data = _rag_engine.extract_structured_data(
            prompt_type=request.prompt_type,
            document_id=request.document_id,
            document_type=request.document_type,
        )
        return ExtractionResponse(
            title=request.prompt_type,
            data=data,
            model_used=settings.llm_model_name,
        )
    except Exception as e:
        logger.error(f"Extraction failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )

@router.get(
    "/history",
    response_model=ChatHistoryResponse,
)
async def get_chat_history():
    """
    Get the full chat history for the current session.

    Returns all question-answer exchanges with citations,
    ordered from oldest to newest.
    """
    return ChatHistoryResponse(
        total_messages=len(_chat_history),
        messages=_chat_history,
    )


@router.delete("/history")
async def clear_chat_history():
    """Clear all chat history."""
    count = len(_chat_history)
    _chat_history.clear()

    logger.info(f"Chat history cleared ({count} messages)")

    return {
        "status": "success",
        "message": f"Cleared {count} messages from chat history.",
    }
