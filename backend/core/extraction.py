"""
PDF Text Extraction Module
───────────────────────────
Extracts raw text from PDF files using PyMuPDF (fitz).
Returns structured page-level text for downstream processing.
"""

import fitz  # PyMuPDF
from pathlib import Path
from loguru import logger


class PDFExtractionError(Exception):
    """Raised when PDF text extraction fails."""
    pass


def extract_text_from_pdf(file_path: str | Path) -> list[dict]:
    """
    Extract text from each page of a PDF file.

    Args:
        file_path: Path to the PDF file.

    Returns:
        List of dicts, each containing:
            - page_number (int): 1-indexed page number
            - text (str): Raw extracted text from that page
            - char_count (int): Number of characters on the page

    Raises:
        PDFExtractionError: If the file cannot be read or has no extractable text.
    """
    file_path = Path(file_path)

    if not file_path.exists():
        raise PDFExtractionError(f"File not found: {file_path}")

    if not file_path.suffix.lower() == ".pdf":
        raise PDFExtractionError(f"Not a PDF file: {file_path}")

    try:
        doc = fitz.open(str(file_path))
    except Exception as e:
        raise PDFExtractionError(f"Failed to open PDF: {e}")

    pages = []
    total_chars = 0

    for page_num in range(len(doc)):
        page = doc[page_num]
        text = page.get_text("text")  # Plain text extraction

        if text.strip():
            page_data = {
                "page_number": page_num + 1,  # 1-indexed
                "text": text,
                "char_count": len(text),
            }
            pages.append(page_data)
            total_chars += len(text)

    doc.close()

    if not pages:
        raise PDFExtractionError(
            f"No extractable text found in {file_path.name}. "
            "The PDF may be image-based (scanned). OCR is not supported yet."
        )

    logger.info(
        f"Extracted {len(pages)} pages, {total_chars:,} chars from {file_path.name}"
    )
    return pages


def get_pdf_metadata(file_path: str | Path) -> dict:
    """
    Get basic metadata from a PDF file.

    Returns:
        Dict with keys: total_pages, file_size_bytes, filename
    """
    file_path = Path(file_path)

    try:
        doc = fitz.open(str(file_path))
        total_pages = len(doc)
        doc.close()
    except Exception as e:
        raise PDFExtractionError(f"Failed to read PDF metadata: {e}")

    return {
        "total_pages": total_pages,
        "file_size_bytes": file_path.stat().st_size,
        "filename": file_path.name,
    }
