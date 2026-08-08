"""
resume_parser.py — Extract plain text from resume files (PDF or TXT).

Supports:
  - PDF: uses pdfplumber (handles most modern CVs well)
  - TXT: raw UTF-8 decode with fallback to latin-1

The output is plain text that gets passed directly into LLM prompts,
so we do minimal post-processing (just strip excess whitespace).
"""

import io
import re
from pathlib import Path

import pdfplumber

from src.logger import get_logger

logger = get_logger(__name__)


def parse_resume(file_bytes: bytes, filename: str) -> str:
    """
    Extract text from a resume file.

    Args:
        file_bytes: Raw bytes of the uploaded file.
        filename:   Original filename (used to detect type by extension).

    Returns:
        Plain text content of the resume, cleaned of excessive whitespace.

    Raises:
        ValueError: If the file type is unsupported.
        RuntimeError: If PDF extraction fails.
    """
    ext = Path(filename).suffix.lower()

    if ext == ".pdf":
        return _extract_pdf(file_bytes)
    elif ext in (".txt", ".md"):
        return _extract_text(file_bytes)
    else:
        raise ValueError(
            f"Unsupported file type '{ext}'. Please upload a .pdf or .txt file."
        )


def _extract_pdf(file_bytes: bytes) -> str:
    """Use pdfplumber to extract text from a PDF resume."""
    try:
        text_parts: list[str] = []
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            logger.debug(f"Parsing PDF with {len(pdf.pages)} pages")
            for page_num, page in enumerate(pdf.pages, start=1):
                page_text = page.extract_text(x_tolerance=2, y_tolerance=2)
                if page_text:
                    text_parts.append(page_text)
                else:
                    logger.warning(f"No text extracted from page {page_num}")

        full_text = "\n\n".join(text_parts)
        cleaned = _clean_whitespace(full_text)

        if not cleaned.strip():
            raise RuntimeError(
                "PDF appears to contain no extractable text. "
                "It may be a scanned image — please use a text-based PDF."
            )

        logger.info(
            f"PDF parsed successfully",
            extra={"char_count": len(cleaned), "page_count": len(text_parts)},
        )
        return cleaned

    except RuntimeError:
        raise
    except Exception as err:
        raise RuntimeError(f"Failed to parse PDF: {err}") from err


def _extract_text(file_bytes: bytes) -> str:
    """Decode a plain-text resume file."""
    try:
        text = file_bytes.decode("utf-8")
    except UnicodeDecodeError:
        text = file_bytes.decode("latin-1")

    cleaned = _clean_whitespace(text)
    logger.info("Text file parsed", extra={"char_count": len(cleaned)})
    return cleaned


def _clean_whitespace(text: str) -> str:
    """Collapse 3+ consecutive newlines into 2, strip trailing spaces."""
    # Remove trailing spaces on each line
    text = "\n".join(line.rstrip() for line in text.splitlines())
    # Collapse excessive blank lines
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()
