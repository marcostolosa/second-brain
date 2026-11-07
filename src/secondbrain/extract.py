"""Content extraction: HTML articles, PDFs (text layer), and plain Markdown/text.

Article extraction prefers trafilatura; when it is unavailable it falls back to a
built-in BeautifulSoup/stdlib extractor so the pipeline never blocks. PDFs without
a text layer are marked needs_extraction (OCR is an optional, documented extra),
never faked.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

__all__ = ["Extracted", "extract_article", "extract_pdf", "extract_text_file", "PdfNeedsOCR"]


class PdfNeedsOCR(Exception):
    """PDF has no extractable text layer; OCR required (optional feature)."""


@dataclass
class Extracted:
    title: str | None
    author: str | None
    published_at: str | None
    text: str
    engine: str


def extract_article(html: bytes, url: str) -> Extracted:
    decoded = html.decode("utf-8", errors="replace")
    try:
        import trafilatura  # type: ignore

        text = trafilatura.extract(decoded, url=url, include_comments=False,
                                   include_tables=True, favor_recall=True) or ""
        meta = trafilatura.extract_metadata(decoded, default_url=url)
        if text.strip():
            return Extracted(
                title=getattr(meta, "title", None),
                author=getattr(meta, "author", None),
                published_at=getattr(meta, "date", None),
                text=text,
                engine="trafilatura",
            )
    except Exception:
        # fall through to the built-in extractor
        pass

    return _extract_with_bs4(decoded)


def _extract_with_bs4(decoded: str) -> Extracted:
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(decoded, "html.parser")
    title = None
    if soup.title and soup.title.string:
        title = soup.title.string.strip()
    og = soup.find("meta", attrs={"property": "og:title"})
    if og and og.get("content"):
        title = og["content"].strip()
    author = None
    am = soup.find("meta", attrs={"name": "author"})
    if am and am.get("content"):
        author = am["content"].strip()
    published = None
    for sel in ({"property": "article:published_time"}, {"name": "date"}):
        dm = soup.find("meta", attrs=sel)
        if dm and dm.get("content"):
            published = dm["content"].strip()
            break

    for tag in soup(["script", "style", "nav", "footer", "aside", "form", "noscript"]):
        tag.decompose()
    main = soup.find("article") or soup.find("main") or soup.body or soup
    text = "\n".join(line.strip() for line in main.get_text("\n").splitlines() if line.strip())
    return Extracted(title=title, author=author, published_at=published, text=text, engine="bs4")


def extract_pdf(path: str | Path) -> tuple[str, int]:
    """Return (text, page_count). Raises PdfNeedsOCR if no text layer is found."""
    from pypdf import PdfReader

    reader = PdfReader(str(path))
    pages = len(reader.pages)
    parts = []
    for page in reader.pages:
        parts.append(page.extract_text() or "")
    text = "\n\n".join(parts).strip()
    if not text:
        raise PdfNeedsOCR(f"no text layer in {path} ({pages} pages)")
    return text, pages


def extract_text_file(path: str | Path) -> str:
    return Path(path).read_text(encoding="utf-8", errors="replace")
