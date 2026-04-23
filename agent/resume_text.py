from __future__ import annotations

from pathlib import Path


def extract_resume_text(resume_path: str, max_chars: int = 8000) -> str:
    """
    Best-effort resume text extraction (offline).
    Keeps output bounded so we don't blow up LLM context.
    """
    if not resume_path:
        return ""
    path = Path(resume_path)
    if not path.exists():
        return ""
    if path.suffix.lower() != ".pdf":
        try:
            return path.read_text(encoding="utf-8")[:max_chars]
        except Exception:
            return ""

    try:
        from pypdf import PdfReader
    except Exception:
        return ""

    try:
        reader = PdfReader(str(path))
        parts: list[str] = []
        for page in reader.pages[:20]:
            text = page.extract_text() or ""
            text = " ".join(text.split())
            if text:
                parts.append(text)
            if sum(len(p) for p in parts) >= max_chars:
                break
        return "\n".join(parts)[:max_chars]
    except Exception:
        return ""
