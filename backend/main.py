"""
Enterprise RAG Document Intelligence Platform
──────────────────────────────────────────────
FastAPI application entry point.

Startup flow:
    1. Load settings from .env
    2. Pre-warm embedding model (avoids cold-start on first request)
    3. Initialize ChromaDB connection
    4. Register API routes
    5. Start Uvicorn server
"""

import os
os.environ["CUDA_VISIBLE_DEVICES"] = ""
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
os.environ["MKL_THREADING_TYPE"] = "SEQUENCE"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["USE_TF"] = "NO"
os.environ["USE_TORCH"] = "YES"

import torch

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from config import settings
from api.routes.documents import router as documents_router
from api.routes.query import router as query_router


# ─── Lifespan (startup / shutdown) ───────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Pre-warm expensive resources on startup and setup logging."""
    
    # Configure structured logging
    logger.add(
        "logs/rag_app_{time}.log",
        rotation="10 MB",
        retention="7 days",
        level="INFO",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {module}:{function}:{line} - {message}"
    )

    logger.info("=" * 60)
    logger.info("🚀 Starting RAG Document Intelligence Platform")
    logger.info("=" * 60)

    # Pre-load embedding model (takes ~2-5 seconds)
    logger.info("Loading embedding model...")
    from core.embedding import EmbeddingEngine
    engine = EmbeddingEngine()
    logger.info(f"✅ Embedding model ready (dim={engine.dimension})")

    # Initialize vector store connection
    logger.info("Connecting to ChromaDB...")
    from core.vector_store import VectorStore
    store = VectorStore()
    stats = store.get_stats()
    logger.info(f"✅ ChromaDB ready ({stats['total_vectors']} vectors)")

    logger.info("=" * 60)
    logger.info("✅ All systems ready. Accepting requests.")
    logger.info("=" * 60)

    yield  # ── App is running ──

    logger.info("Shutting down RAG platform...")


# ─── App Factory ─────────────────────────────────────────────

app = FastAPI(
    title="RAG Document Intelligence Platform",
    description=(
        "Enterprise AI system for document analysis using "
        "Retrieval-Augmented Generation (RAG), vector search, "
        "and LLMs with citation-based answers."
    ),
    version="1.0.0",
    lifespan=lifespan,
)


# ─── CORS (allow React frontend) ────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for easy Vercel deployment (in production, set this to your Vercel URL)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Register Routes ────────────────────────────────────────

app.include_router(documents_router, prefix="/api", tags=["Documents"])
app.include_router(query_router, prefix="/api", tags=["Query & Chat"])


# ─── Health Check ────────────────────────────────────────────

@app.get("/", tags=["Health"])
async def health_check():
    """Root endpoint — confirms the API is running."""
    return {
        "status": "healthy",
        "service": "RAG Document Intelligence Platform",
        "version": "1.0.0",
    }


@app.get("/api/health", tags=["Health"])
async def detailed_health():
    """Detailed health check with system stats."""
    from core.vector_store import VectorStore
    store = VectorStore()
    stats = store.get_stats()

    return {
        "status": "healthy",
        "embedding_model": settings.embedding_model_name,
        "llm_model": settings.llm_model_name,
        "vector_store": stats,
        "config": {
            "chunk_size": settings.chunk_size,
            "chunk_overlap": settings.chunk_overlap,
            "top_k": settings.top_k_results,
            "similarity_threshold": settings.similarity_threshold,
        },
    }


# ─── Run ─────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=True,
        log_level="info",
    )
