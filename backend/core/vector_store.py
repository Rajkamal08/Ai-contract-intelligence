"""
Vector Store Module (ChromaDB)
──────────────────────────────
Manages all interactions with ChromaDB: storing embeddings,
querying for similar documents, and managing collections.
"""

import chromadb
from chromadb.config import Settings as ChromaSettings
from loguru import logger
from config import settings
from core.chunking import TextChunk


class VectorStore:
    """
    ChromaDB vector store wrapper.

    Handles:
        - Collection creation/management
        - Storing chunks with embeddings and metadata
        - Similarity search with filtering
        - Document deletion
    """

    _instance = None
    _client = None
    _collection = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if self._client is None:
            self._initialize()

    def _initialize(self):
        """Initialize ChromaDB client and collection."""
        persist_dir = str(settings.chroma_path)

        logger.info(f"Initializing ChromaDB at: {persist_dir}")

        self._client = chromadb.PersistentClient(
            path=persist_dir,
            settings=ChromaSettings(anonymized_telemetry=False),
        )

        self._collection = self._client.get_or_create_collection(
            name=settings.chroma_collection_name,
            metadata={"hnsw:space": "cosine"},  # Cosine similarity
        )

        logger.info(
            f"ChromaDB initialized. Collection '{settings.chroma_collection_name}' "
            f"has {self._collection.count()} vectors"
        )

    @property
    def collection(self):
        return self._collection

    def store_chunks(
        self,
        chunks: list[TextChunk],
        embeddings: list[list[float]],
    ) -> int:
        """
        Store text chunks with their embeddings in ChromaDB.

        Args:
            chunks: List of TextChunk objects.
            embeddings: Corresponding embedding vectors.

        Returns:
            Number of chunks stored.
        """
        if len(chunks) != len(embeddings):
            raise ValueError(
                f"Mismatch: {len(chunks)} chunks vs {len(embeddings)} embeddings"
            )

        ids = [chunk.chunk_id for chunk in chunks]
        documents = [chunk.text for chunk in chunks]
        metadatas = []
        for chunk in chunks:
            meta = {
                "document_id": chunk.document_id,
                "filename": chunk.filename,
                "page_number": chunk.page_number,
                "chunk_index": chunk.chunk_index,
                "char_count": chunk.char_count,
                "document_type": getattr(chunk, 'document_type', 'General'),
            }
            if getattr(chunk, 'risk_score', None) is not None:
                meta["risk_score"] = chunk.risk_score
            metadatas.append(meta)

        # ChromaDB has a batch limit; split into batches of 5000
        batch_size = 5000
        stored = 0

        for i in range(0, len(ids), batch_size):
            batch_end = min(i + batch_size, len(ids))
            self._collection.add(
                ids=ids[i:batch_end],
                embeddings=embeddings[i:batch_end],
                documents=documents[i:batch_end],
                metadatas=metadatas[i:batch_end],
            )
            stored += batch_end - i

        logger.info(
            f"Stored {stored} chunks in ChromaDB. "
            f"Total vectors: {self._collection.count()}"
        )
        return stored

    def search(
        self,
        query_embedding: list[float],
        top_k: int | None = None,
        document_id: str | None = None,
        document_type: str | None = None,
    ) -> list[dict]:
        """
        Perform similarity search in the vector store.

        Args:
            query_embedding: The query vector.
            top_k: Number of results to return.
            document_id: Optional filter to search within a specific document.
            document_type: Optional filter to search within a specific document type.

        Returns:
            List of dicts with keys: text, metadata, similarity_score
        """
        top_k = top_k or settings.top_k_results

        # Build where filter
        where_filter = None
        if document_id:
            where_filter = {"document_id": document_id}
        elif document_type:
            where_filter = {"document_type": document_type}

        results = self._collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=where_filter,
            include=["documents", "metadatas", "distances"],
        )

        # Parse results
        parsed = []
        if results["documents"] and results["documents"][0]:
            for i in range(len(results["documents"][0])):
                # ChromaDB returns cosine distance; convert to similarity
                distance = results["distances"][0][i]
                similarity = 1 - distance  # cosine similarity = 1 - cosine distance

                parsed.append({
                    "text": results["documents"][0][i],
                    "metadata": results["metadatas"][0][i],
                    "similarity_score": round(similarity, 4),
                })

        logger.info(
            f"Search returned {len(parsed)} results "
            f"(top score: {parsed[0]['similarity_score'] if parsed else 'N/A'})"
        )
        return parsed

    def delete_document(self, document_id: str) -> int:
        """
        Delete all chunks belonging to a specific document.

        Returns:
            Number of chunks deleted.
        """
        # Get all chunk IDs for this document
        results = self._collection.get(
            where={"document_id": document_id},
            include=[],
        )

        if not results["ids"]:
            logger.warning(f"No chunks found for document_id: {document_id}")
            return 0

        count = len(results["ids"])
        self._collection.delete(ids=results["ids"])

        logger.info(f"Deleted {count} chunks for document_id: {document_id}")
        return count

    def get_document_chunks(self, document_id: str) -> list[dict]:
        """Get all chunks for a specific document."""
        results = self._collection.get(
            where={"document_id": document_id},
            include=["documents", "metadatas"],
        )

        chunks = []
        for i in range(len(results["ids"])):
            chunks.append({
                "id": results["ids"][i],
                "text": results["documents"][i],
                "metadata": results["metadatas"][i],
            })

        return chunks

    def get_stats(self) -> dict:
        """Get vector store statistics."""
        return {
            "total_vectors": self._collection.count(),
            "collection_name": settings.chroma_collection_name,
        }
