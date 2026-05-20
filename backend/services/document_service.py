"""
Document Service — Ingestion Pipeline Orchestrator
───────────────────────────────────────────────────
Orchestrates the full document ingestion pipeline:
    PDF Upload → Extraction → Cleaning → Chunking → Embedding → Vector Store

This is the service layer that ties all core modules together.
"""

import uuid
import shutil
from pathlib import Path
from datetime import datetime, timezone
from loguru import logger

from config import settings
from core.extraction import extract_text_from_pdf, get_pdf_metadata
from core.cleaning import clean_pages
from core.chunking import ChunkingEngine
from core.embedding import EmbeddingEngine
from core.vector_store import VectorStore
from models.schemas import DocumentMetadata


# In-memory document registry (swap for DB in production)
_document_registry: dict[str, DocumentMetadata] = {}


class DocumentService:
    """
    Orchestrates the full document ingestion pipeline.

    Pipeline: Upload → Extract → Clean → Chunk → Embed → Store
    """

    def __init__(self):
        self.chunking_engine = ChunkingEngine()
        self.embedding_engine = EmbeddingEngine()
        self.vector_store = VectorStore()
        self._load_existing_documents()

    def _load_existing_documents(self):
        """Reconstruct _document_registry from stored vectors in ChromaDB."""
        global _document_registry
        try:
            results = self.vector_store.collection.get(include=["metadatas"])
            if not results or not results.get("metadatas"):
                return

            # Group by document_id
            docs_info = {}
            for meta in results["metadatas"]:
                doc_id = meta.get("document_id")
                filename = meta.get("filename", "Unknown PDF")
                page_number = meta.get("page_number", 1)

                if not doc_id:
                    continue

                if doc_id not in docs_info:
                    docs_info[doc_id] = {
                        "filename": filename,
                        "pages": set(),
                        "chunks_count": 0,
                        "document_type": meta.get("document_type", "General"),
                        "risk_score": meta.get("risk_score"),
                    }
                
                docs_info[doc_id]["pages"].add(page_number)
                docs_info[doc_id]["chunks_count"] += 1

            # Populate the registry
            for doc_id, info in docs_info.items():
                if doc_id not in _document_registry:
                    upload_time = datetime.now(timezone.utc)
                    file_path = settings.upload_path / info["filename"]
                    file_size = 0
                    if file_path.exists():
                        file_size = file_path.stat().st_size
                        upload_time = datetime.fromtimestamp(file_path.stat().st_mtime, tz=timezone.utc)

                    _document_registry[doc_id] = DocumentMetadata(
                        document_id=doc_id,
                        filename=info["filename"],
                        upload_time=upload_time,
                        total_pages=len(info["pages"]) if info["pages"] else 1,
                        total_chunks=info["chunks_count"],
                        file_size_bytes=file_size,
                        document_type=info.get("document_type", "General"),
                        risk_score=info.get("risk_score"),
                    )
            logger.info(f"Loaded {len(_document_registry)} documents from ChromaDB on startup")
        except Exception as e:
            logger.error(f"Failed to load existing documents from ChromaDB: {e}")

    async def ingest_document(self, file_path: Path, original_filename: str, document_type: str = "General") -> DocumentMetadata:
        """
        Run the full ingestion pipeline on an uploaded PDF.

        Args:
            file_path: Path to the saved PDF file.
            original_filename: Original filename from the upload.
            document_type: The type of document (e.g., NDA, Employment Contract)

        Returns:
            DocumentMetadata with ingestion results.
        """
        document_id = str(uuid.uuid4())
        logger.info(f"Starting ingestion: {original_filename} → {document_id}")

        try:
            # ── Step 1: Get PDF metadata ──────────────────
            pdf_meta = get_pdf_metadata(file_path)
            logger.info(f"  PDF: {pdf_meta['total_pages']} pages, {pdf_meta['file_size_bytes']:,} bytes")

            # ── Step 2: Extract text ──────────────────────
            pages = extract_text_from_pdf(file_path)
            logger.info(f"  Extracted: {len(pages)} pages with text")

            # ── Step 3: Clean text ────────────────────────
            cleaned_pages = clean_pages(pages)
            logger.info(f"  Cleaned: {len(cleaned_pages)} pages retained")

            # ── Step 4: Chunk text ────────────────────────
            chunks = self.chunking_engine.chunk_pages(
                pages=cleaned_pages,
                document_id=document_id,
                filename=original_filename,
            )
            # Add document_type and initial risk_score to chunk metadata so it can be retrieved on restart
            for chunk in chunks:
                chunk.document_type = document_type
                chunk.risk_score = None
            logger.info(f"  Chunked: {len(chunks)} chunks created")

            # ── Step 5: Generate embeddings ───────────────
            chunk_texts = [chunk.text for chunk in chunks]
            embeddings = self.embedding_engine.embed_batch(chunk_texts)
            logger.info(f"  Embedded: {len(embeddings)} vectors generated")

            # ── Step 6: Store in vector DB ────────────────
            stored = self.vector_store.store_chunks(chunks, embeddings)
            logger.info(f"  Stored: {stored} vectors in ChromaDB")

            # ── Build metadata ────────────────────────────
            import random
            
            # Simple mock for Automated Risk Scoring for demonstration
            # In a full implementation, we would call rag_engine.extract_structured_data here
            calculated_risk = None
            if document_type in ["NDA", "Employment Contract", "Vendor Agreement"]:
                calculated_risk = random.randint(15, 85)
                
            doc_meta = DocumentMetadata(
                document_id=document_id,
                filename=original_filename,
                upload_time=datetime.now(timezone.utc),
                total_pages=pdf_meta["total_pages"],
                total_chunks=len(chunks),
                file_size_bytes=pdf_meta["file_size_bytes"],
                document_type=document_type,
                risk_score=calculated_risk,
            )

            # Register document
            _document_registry[document_id] = doc_meta

            # We must also update the metadata in ChromaDB so it persists across restarts
            # We will do this asynchronously or on next update, but for now we'll just let Chroma keep the chunks and
            # update the in-memory registry. A more robust solution updates the Chroma metadata.
            
            logger.info(
                f"✅ Ingestion complete: {original_filename} → "
                f"{len(chunks)} chunks stored"
            )

            return doc_meta

        except Exception as e:
            logger.error(f"❌ Ingestion failed for {original_filename}: {e}")
            # Cleanup partial data
            self.vector_store.delete_document(document_id)
            raise

    def list_documents(self) -> list[DocumentMetadata]:
        """Return all ingested documents."""
        return list(_document_registry.values())

    def get_document(self, document_id: str) -> DocumentMetadata | None:
        """Get a specific document's metadata."""
        return _document_registry.get(document_id)

    def delete_document(self, document_id: str) -> bool:
        """Delete a document and all its chunks from the vector store."""
        if document_id not in _document_registry:
            return False

        self.vector_store.delete_document(document_id)
        del _document_registry[document_id]
        logger.info(f"Deleted document: {document_id}")
        return True
