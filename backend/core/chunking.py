"""
Semantic Chunking Engine
────────────────────────
Splits cleaned text into overlapping chunks optimized for embedding
and retrieval. Uses recursive character-based splitting with
configurable chunk size and overlap.
"""

from dataclasses import dataclass
from loguru import logger
from config import settings


@dataclass
class TextChunk:
    """A single text chunk with metadata."""
    text: str
    chunk_index: int
    page_number: int
    document_id: str
    filename: str
    char_count: int
    document_type: str = "General"
    risk_score: int | None = None

    @property
    def chunk_id(self) -> str:
        """Unique ID: doc_id + chunk_index."""
        return f"{self.document_id}_chunk_{self.chunk_index}"


class ChunkingEngine:
    """
    Recursive text splitter with overlap.

    Strategy:
        1. Try splitting on paragraph boundaries (\\n\\n)
        2. Fall back to sentence boundaries (. ! ?)
        3. Fall back to word boundaries (spaces)
        4. Last resort: hard character split

    Each chunk gets overlap from the previous chunk to maintain
    context continuity across chunk boundaries.
    """

    # Separators ordered by preference (most semantic → least)
    SEPARATORS = ["\n\n", "\n", ". ", "! ", "? ", "; ", ", ", " "]

    def __init__(
        self,
        chunk_size: int | None = None,
        chunk_overlap: int | None = None,
    ):
        self.chunk_size = chunk_size or settings.chunk_size
        self.chunk_overlap = chunk_overlap or settings.chunk_overlap

        if self.chunk_overlap >= self.chunk_size:
            raise ValueError(
                f"chunk_overlap ({self.chunk_overlap}) must be less than "
                f"chunk_size ({self.chunk_size})"
            )

    def chunk_pages(
        self,
        pages: list[dict],
        document_id: str,
        filename: str,
    ) -> list[TextChunk]:
        """
        Chunk all pages of a document.

        Args:
            pages: List of page dicts with 'text' and 'page_number'.
            document_id: Unique document identifier.
            filename: Original filename.

        Returns:
            List of TextChunk objects with metadata.
        """
        all_chunks: list[TextChunk] = []
        global_chunk_index = 0

        for page in pages:
            page_text = page["text"]
            page_number = page["page_number"]

            # Split this page's text into chunks
            raw_chunks = self._recursive_split(page_text)

            for raw_chunk in raw_chunks:
                chunk = TextChunk(
                    text=raw_chunk,
                    chunk_index=global_chunk_index,
                    page_number=page_number,
                    document_id=document_id,
                    filename=filename,
                    char_count=len(raw_chunk),
                )
                all_chunks.append(chunk)
                global_chunk_index += 1

        # Validate chunks
        all_chunks = self._validate_chunks(all_chunks)

        logger.info(
            f"Created {len(all_chunks)} chunks from {len(pages)} pages "
            f"(avg {sum(c.char_count for c in all_chunks) // max(len(all_chunks), 1)} chars/chunk)"
        )

        return all_chunks

    def _recursive_split(self, text: str) -> list[str]:
        """
        Recursively split text using separator hierarchy.
        Applies overlap between consecutive chunks.
        """
        if len(text) <= self.chunk_size:
            return [text.strip()] if text.strip() else []

        chunks = []
        current_chunks = self._split_by_separators(text)

        # Merge small splits back together up to chunk_size
        merged = self._merge_splits(current_chunks)

        # Apply overlap
        if self.chunk_overlap > 0 and len(merged) > 1:
            merged = self._apply_overlap(merged)

        for chunk in merged:
            stripped = chunk.strip()
            if stripped:
                chunks.append(stripped)

        return chunks

    def _split_by_separators(self, text: str) -> list[str]:
        """Split text using the first separator that produces reasonable chunks."""
        for separator in self.SEPARATORS:
            if separator in text:
                splits = text.split(separator)

                # Check if this separator produces useful splits
                # (at least one split should be smaller than chunk_size)
                if any(len(s) <= self.chunk_size for s in splits):
                    # Re-attach separator to maintain sentence structure
                    if separator.strip():  # Not pure whitespace
                        result = []
                        for i, s in enumerate(splits):
                            if i < len(splits) - 1:
                                result.append(s + separator)
                            else:
                                result.append(s)
                        return result
                    return splits

        # Last resort: hard character split
        return [
            text[i: i + self.chunk_size]
            for i in range(0, len(text), self.chunk_size)
        ]

    def _merge_splits(self, splits: list[str]) -> list[str]:
        """Merge small splits into chunks up to chunk_size."""
        merged = []
        current = ""

        for split in splits:
            # If adding this split would exceed chunk_size
            if current and len(current) + len(split) > self.chunk_size:
                if current.strip():
                    merged.append(current.strip())
                current = split
            else:
                current += split

        # Don't forget the last chunk
        if current.strip():
            merged.append(current.strip())

        return merged

    def _apply_overlap(self, chunks: list[str]) -> list[str]:
        """Add overlap from the end of previous chunk to the start of next."""
        if len(chunks) <= 1:
            return chunks

        overlapped = [chunks[0]]

        for i in range(1, len(chunks)):
            prev = chunks[i - 1]
            # Take last `chunk_overlap` characters from previous chunk
            overlap_text = prev[-self.chunk_overlap:]

            # Find a clean word boundary in the overlap
            space_idx = overlap_text.find(" ")
            if space_idx != -1:
                overlap_text = overlap_text[space_idx + 1:]

            overlapped.append(overlap_text + " " + chunks[i])

        return overlapped

    def _validate_chunks(self, chunks: list[TextChunk]) -> list[TextChunk]:
        """
        Validate and filter chunks.
        Remove chunks that are too small to be useful.
        """
        MIN_CHUNK_CHARS = 20  # Chunks smaller than this are noise

        valid = []
        removed = 0

        for chunk in chunks:
            if chunk.char_count >= MIN_CHUNK_CHARS:
                valid.append(chunk)
            else:
                removed += 1

        if removed > 0:
            logger.warning(f"Removed {removed} chunks below minimum size ({MIN_CHUNK_CHARS} chars)")

        return valid
