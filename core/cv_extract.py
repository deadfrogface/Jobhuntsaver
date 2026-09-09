"""CV / document text extraction (PDF, DOCX, plain text)."""

from __future__ import annotations

from pathlib import Path

SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".doc", ".txt", ".md"}


def extract_text(file_path: Path) -> str:
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    ext = file_path.suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise ValueError(f"Unsupported file type: {ext}")
    if ext == ".pdf":
        return _extract_from_pdf(file_path)
    if ext in (".docx", ".doc"):
        return _extract_from_docx(file_path)
    return file_path.read_text(encoding="utf-8", errors="replace")


def _extract_from_pdf(file_path: Path) -> str:
    try:
        from pypdf import PdfReader
    except ImportError:
        try:
            from PyPDF2 import PdfReader  # type: ignore
        except ImportError as exc:
            raise RuntimeError("Install pypdf for PDF extraction") from exc
    reader = PdfReader(str(file_path))
    pages = []
    for page in reader.pages:
        text = page.extract_text() or ""
        if text.strip():
            pages.append(text.strip())
    return "\n\n".join(pages)


def _extract_from_docx(file_path: Path) -> str:
    from docx import Document

    doc = Document(str(file_path))
    return "\n\n".join(p.text.strip() for p in doc.paragraphs if p.text.strip())
