"""
Retrieval Module
────────────────
Handles the retrieval step of RAG: takes a user query,
generates its embedding, searches the vector store,
and returns the most relevant chunks with relevance filtering.
"""

from loguru import logger
from config import settings
from core.embedding import EmbeddingEngine
from core.vector_store import VectorStore


class RetrievalEngine:
    """
    Retrieval engine for RAG pipeline.

    Steps:
        1. Embed the user query
        2. Search vector store for top-k similar chunks
        3. Filter by similarity threshold
        4. Return ranked results
    """

    def __init__(self):
        self.embedding_engine = EmbeddingEngine()
        self.vector_store = VectorStore()

    def retrieve(
        self,
        query: str,
        top_k: int | None = None,
        document_id: str | None = None,
        document_type: str | None = None,
        similarity_threshold: float | None = None,
    ) -> list[dict]:
        """
        Retrieve relevant chunks for a query.

        Args:
            query: User's question/query text.
            top_k: Number of results to retrieve.
            document_id: Optional filter to search within a specific document.
            document_type: Optional filter to search within a specific document type.
            similarity_threshold: Minimum similarity score to include.

        Returns:
            List of relevant chunks sorted by similarity score (descending).
            Each dict has keys: text, metadata, similarity_score
        """
        top_k = top_k or settings.top_k_results
        similarity_threshold = similarity_threshold or settings.similarity_threshold

        # Step 1: Embed the query
        logger.info(f"Embedding query: '{query[:80]}...'")
        query_embedding = self.embedding_engine.embed_query(query)

        # Step 2: Search vector store
        results = self.vector_store.search(
            query_embedding=query_embedding,
            top_k=top_k,
            document_id=document_id,
            document_type=document_type,
        )

        # Step 3: Filter by similarity threshold
        filtered = [
            r for r in results
            if r["similarity_score"] >= similarity_threshold
        ]

        if len(filtered) < len(results):
            logger.info(
                f"Filtered {len(results) - len(filtered)} results below "
                f"threshold ({similarity_threshold})"
            )

        # Step 4: Sort by score (highest first)
        filtered.sort(key=lambda x: x["similarity_score"], reverse=True)

        logger.info(
            f"Retrieved {len(filtered)} relevant chunks for query "
            f"(threshold: {similarity_threshold})"
        )

        return filtered
