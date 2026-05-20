"""
RAG Engine — The Core ML Module
────────────────────────────────
Orchestrates the full RAG pipeline:
    1. Retrieves relevant context from vector store
    2. Builds a grounded prompt with citations
    3. Calls Groq LLM with strict no-hallucination instructions
    4. Parses response and attaches source citations

This is the MOST CRITICAL module — answers MUST come ONLY from retrieved context.
"""

from groq import Groq
from loguru import logger
from config import settings
from core.retrieval import RetrievalEngine
from models.schemas import Citation, QueryResponse


# ─── System Prompt (NO HALLUCINATION ENFORCED) ────────────

SYSTEM_PROMPT = """You are an enterprise AI document assistant. Your ONLY job is to answer questions using the provided context.

STRICT RULES:
1. ONLY use information from the CONTEXT below to answer.
2. If the context does NOT contain enough information, say: "I cannot find sufficient information in the uploaded documents to answer this question."
3. NEVER make up facts, statistics, or information not present in the context.
4. NEVER use your general knowledge — only the provided context.
5. When answering, reference which source(s) you used by mentioning [Source X].
6. Keep answers clear, structured, and professional.
7. If the question is ambiguous, state what you're interpreting it as before answering.

CONTEXT FORMAT:
Each context block is labeled [Source 1], [Source 2], etc. with metadata about the source document and page."""

USER_PROMPT_TEMPLATE = """CONTEXT:
{context}

─────────────────────────────
QUESTION: {question}

Provide a comprehensive answer based ONLY on the context above. Reference your sources using [Source X] notation."""


class RAGEngine:
    """
    Full RAG pipeline: Retrieve → Build Context → Call LLM → Return with Citations.
    """

    def __init__(self):
        self.retrieval_engine = RetrievalEngine()
        self._groq_client = None

    @property
    def groq_client(self) -> Groq:
        """Lazy-load Groq client."""
        if self._groq_client is None:
            if not settings.groq_api_key:
                raise RuntimeError(
                    "GROQ_API_KEY is not set. Add it to your .env file."
                )
            self._groq_client = Groq(api_key=settings.groq_api_key)
        return self._groq_client

    def query(
        self,
        question: str,
        top_k: int | None = None,
        document_id: str | None = None,
        document_type: str | None = None,
    ) -> QueryResponse:
        """
        Execute the full RAG pipeline.

        Args:
            question: User's question.
            top_k: Number of chunks to retrieve.
            document_id: Optional filter for specific document.
            document_type: Optional filter for specific document type.

        Returns:
            QueryResponse with answer, citations, and metadata.
        """
        logger.info(f"RAG query: '{question[:100]}'")

        # ── Step 1: Retrieve relevant chunks ──────────────
        retrieved_chunks = self.retrieval_engine.retrieve(
            query=question,
            top_k=top_k,
            document_id=document_id,
            document_type=document_type,
        )

        if not retrieved_chunks:
            logger.warning("No relevant chunks found for query")
            return QueryResponse(
                answer="I cannot find any relevant information in the uploaded documents to answer this question. Please ensure you have uploaded relevant documents first.",
                citations=[],
                total_chunks_retrieved=0,
                model_used=settings.llm_model_name,
                confidence_note="No relevant context found in the document store.",
            )

        # ── Step 2: Build context with source labels ──────
        context = self._build_context(retrieved_chunks)

        # ── Step 3: Build citations ───────────────────────
        citations = self._build_citations(retrieved_chunks)

        # ── Step 4: Call LLM via Groq ─────────────────────
        answer = self._call_llm(question, context)

        # ── Step 5: Build confidence note ─────────────────
        avg_score = sum(c["similarity_score"] for c in retrieved_chunks) / len(retrieved_chunks)
        if avg_score >= 0.7:
            confidence = "High confidence — strong semantic match with source documents."
        elif avg_score >= 0.5:
            confidence = "Moderate confidence — partial match with source documents."
        else:
            confidence = "Low confidence — weak match. The answer may be incomplete."

        logger.info(
            f"RAG complete. {len(citations)} citations, avg_score={avg_score:.3f}"
        )

        return QueryResponse(
            answer=answer,
            citations=citations,
            total_chunks_retrieved=len(retrieved_chunks),
            model_used=settings.llm_model_name,
            confidence_note=confidence,
        )

    def _build_context(self, chunks: list[dict]) -> str:
        """
        Build a formatted context string from retrieved chunks.
        Each chunk is labeled [Source N] with its metadata.
        """
        context_blocks = []

        for i, chunk in enumerate(chunks, 1):
            meta = chunk["metadata"]
            block = (
                f"[Source {i}] "
                f"(File: {meta['filename']}, Page: {meta['page_number']}, "
                f"Similarity: {chunk['similarity_score']:.2f})\n"
                f"{chunk['text']}"
            )
            context_blocks.append(block)

        return "\n\n".join(context_blocks)

    def _build_citations(self, chunks: list[dict]) -> list[Citation]:
        """Build Citation objects from retrieved chunks."""
        citations = []

        for chunk in chunks:
            meta = chunk["metadata"]
            # Truncate text for citation display (first 200 chars)
            preview = chunk["text"][:200]
            if len(chunk["text"]) > 200:
                preview += "..."

            citations.append(Citation(
                source_file=meta["filename"],
                page_number=meta["page_number"],
                chunk_index=meta["chunk_index"],
                relevant_text=preview,
                similarity_score=chunk["similarity_score"],
            ))

        return citations

    def _call_llm(self, question: str, context: str) -> str:
        """
        Call Groq LLM with the grounded prompt.

        Uses the system prompt to enforce no-hallucination behavior.
        """
        user_prompt = USER_PROMPT_TEMPLATE.format(
            context=context,
            question=question,
        )

        try:
            response = self.groq_client.chat.completions.create(
                model=settings.llm_model_name,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.1,  # Low temperature for factual accuracy
                max_tokens=2048,
                top_p=0.9,
            )

            answer = response.choices[0].message.content.strip()
            logger.info(
                f"LLM response received. Tokens: "
                f"prompt={response.usage.prompt_tokens}, "
                f"completion={response.usage.completion_tokens}"
            )
            return answer

        except Exception as e:
            logger.error(f"Groq API call failed: {e}")
            raise RuntimeError(f"LLM call failed: {e}")

    def extract_structured_data(
        self,
        prompt_type: str,
        document_id: str | None = None,
        document_type: str | None = None,
    ) -> dict:
        """
        Execute the RAG pipeline for structured data extraction.
        Forces the LLM to output pure JSON.
        """
        import json

        # Map prompt_type to a specific question and JSON structure
        if prompt_type == "Summarize Liabilities":
            question = "Extract all liabilities, indemnification clauses, and limitations of liability from the document."
            json_schema = '{"liabilities": [{"clause": "string", "description": "string", "risk_level": "High/Medium/Low"}]}'
        elif prompt_type == "Extract Clauses":
            question = "Extract key contract clauses such as parties involved, effective dates, termination, and governing law."
            json_schema = '{"parties": ["string"], "effective_date": "string", "termination_clause": "string", "governing_law": "string"}'
        elif prompt_type == "Identify Non-Compete Terms":
            question = "Identify any non-compete clauses, non-solicitation agreements, or post-employment restrictions."
            json_schema = '{"has_non_compete": bool, "duration": "string", "geographic_scope": "string", "details": "string"}'
        else:
            question = f"Extract information for: {prompt_type}"
            json_schema = '{"extracted_data": "string or array"}'

        # Retrieve chunks
        retrieved_chunks = self.retrieval_engine.retrieve(
            query=question,
            top_k=10,
            document_id=document_id,
            document_type=document_type,
        )

        if not retrieved_chunks:
            return {"error": "No relevant context found to extract data."}

        context = self._build_context(retrieved_chunks)

        system_prompt = f"""You are an enterprise AI contract intelligence assistant.
Your ONLY job is to extract data from the provided context and output it in STRICT JSON format.
DO NOT include any markdown formatting like ```json. Output ONLY the raw parseable JSON object.

REQUIRED SCHEMA:
{json_schema}
"""
        
        user_prompt = f"""CONTEXT:
{context}

─────────────────────────────
TASK: {question}

Extract the requested data from the context above. Output strictly as JSON following the REQUIRED SCHEMA."""

        try:
            response = self.groq_client.chat.completions.create(
                model=settings.llm_model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.0,
                max_tokens=2048,
                response_format={"type": "json_object"},
            )
            answer = response.choices[0].message.content.strip()
            return json.loads(answer)
        except Exception as e:
            logger.error(f"Groq API call failed for structured extraction: {e}")
            raise RuntimeError(f"LLM extraction failed: {e}")
