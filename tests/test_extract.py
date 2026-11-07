"""Acceptance #3: Markdown + PDF (text layer) extraction; OCR flagged, not faked."""

import pytest

from secondbrain.extract import extract_text_file, extract_pdf, PdfNeedsOCR
from secondbrain.hashing import sha256_bytes, sha256_file


def test_markdown_extraction_and_hash(vault):
    p = vault.root / "raw" / "inbox" / "note.md"
    data = b"# Title\n\nbody text here\n"
    p.write_bytes(data)
    assert extract_text_file(p).startswith("# Title")
    assert sha256_file(p) == sha256_bytes(data)


def test_pdf_with_text_layer(monkeypatch):
    class FakePage:
        def __init__(self, t): self._t = t
        def extract_text(self): return self._t

    class FakeReader:
        def __init__(self, path): self.pages = [FakePage("Hello SecondBrain"), FakePage("page two")]

    monkeypatch.setattr("pypdf.PdfReader", FakeReader)
    text, pages = extract_pdf("whatever.pdf")
    assert pages == 2
    assert "Hello SecondBrain" in text


def test_pdf_without_text_layer_needs_ocr(monkeypatch):
    class FakePage:
        def extract_text(self): return ""

    class FakeReader:
        def __init__(self, path): self.pages = [FakePage()]

    monkeypatch.setattr("pypdf.PdfReader", FakeReader)
    with pytest.raises(PdfNeedsOCR):
        extract_pdf("scanned.pdf")
