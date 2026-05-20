"""
Text Cleaning Pipeline
──────────────────────
Cleans raw extracted text to remove noise, normalize formatting,
and prepare text for high-quality chunking and embedding.
"""

import re
import unicodedata
from loguru import logger


def clean_text(raw_text: str) -> str:
    """
    Full cleaning pipeline for raw extracted PDF text.

    Pipeline steps:
        1. Unicode normalization (NFKD → remove control chars)
        2. Fix encoding artifacts (smart quotes, ligatures, etc.)
        3. Normalize whitespace (collapse runs, trim lines)
        4. Remove page artifacts (headers, footers, page numbers)
        5. Remove excessive blank lines
        6. Final strip

    Args:
        raw_text: Raw text from PDF extraction.

    Returns:
        Cleaned text ready for chunking.
    """
    if not raw_text or not raw_text.strip():
        return ""

    text = raw_text

    # Step 1: Unicode normalization
    text = unicodedata.normalize("NFKC", text)

    # Step 2: Fix common encoding artifacts
    text = _fix_encoding_artifacts(text)

    # Step 3: Remove control characters (keep newlines, tabs)
    text = _remove_control_chars(text)

    # Step 4: Normalize whitespace
    text = _normalize_whitespace(text)

    # Step 5: Remove page artifacts
    text = _remove_page_artifacts(text)

    # Step 6: Collapse excessive blank lines (max 2 consecutive)
    text = re.sub(r"\n{3,}", "\n\n", text)

    # Step 7: Final strip
    text = text.strip()

    return text


def clean_pages(pages: list[dict]) -> list[dict]:
    """
    Clean text for all extracted pages.

    Args:
        pages: List of page dicts from extraction (with 'text' key).

    Returns:
        Same list with cleaned 'text' and updated 'char_count'.
    """
    cleaned = []
    total_removed = 0

    for page in pages:
        original_len = len(page["text"])
        cleaned_text = clean_text(page["text"])

        if cleaned_text:  # Skip pages that become empty after cleaning
            cleaned.append({
                "page_number": page["page_number"],
                "text": cleaned_text,
                "char_count": len(cleaned_text),
            })
            total_removed += original_len - len(cleaned_text)

    logger.info(
        f"Cleaned {len(cleaned)} pages, removed {total_removed:,} noise characters"
    )
    return cleaned


# ─── Internal Helper Functions ────────────────────────────


def _fix_encoding_artifacts(text: str) -> str:
    """Replace common encoding artifacts with correct characters."""
    replacements = {
        "\u2018": "'",   # Left single quote
        "\u2019": "'",   # Right single quote
        "\u201c": '"',   # Left double quote
        "\u201d": '"',   # Right double quote
        "\u2013": "-",   # En dash
        "\u2014": "-",   # Em dash
        "\u2026": "...", # Ellipsis
        "\ufb01": "fi",  # fi ligature
        "\ufb02": "fl",  # fl ligature
        "\ufb03": "ffi", # ffi ligature
        "\ufb04": "ffl", # ffl ligature
        "\u00a0": " ",   # Non-breaking space
        "\u200b": "",    # Zero-width space
        "\ufeff": "",    # BOM
    }

    for old, new in replacements.items():
        text = text.replace(old, new)

    return text


def _remove_control_chars(text: str) -> str:
    """Remove control characters except newlines and tabs."""
    return "".join(
        ch for ch in text
        if ch in ("\n", "\t", "\r") or not unicodedata.category(ch).startswith("C")
    )


def _normalize_whitespace(text: str) -> str:
    """Collapse multiple spaces/tabs into single space, preserve newlines."""
    # Replace tabs with spaces
    text = text.replace("\t", " ")

    # Collapse multiple spaces (but not newlines) into one
    text = re.sub(r"[^\S\n]+", " ", text)

    # Strip trailing whitespace from each line
    lines = [line.rstrip() for line in text.split("\n")]
    text = "\n".join(lines)

    return text


def _remove_page_artifacts(text: str) -> str:
    """Remove common PDF page artifacts like headers/footers/page numbers."""
    lines = text.split("\n")
    cleaned_lines = []

    for line in lines:
        stripped = line.strip()

        # Skip standalone page numbers
        if re.match(r"^[\d]+$", stripped):
            continue

        # Skip lines like "Page 5 of 20"
        if re.match(r"^page\s+\d+\s*(of\s+\d+)?$", stripped, re.IGNORECASE):
            continue

        # Skip very short lines that look like headers/footers (< 5 chars)
        # but only if they're isolated (surrounded by blank lines)
        # We keep them for now — overly aggressive filtering loses content

        cleaned_lines.append(line)

    return "\n".join(cleaned_lines)
