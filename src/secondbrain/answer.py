"""Answering: route via Jev (lookup->Sonnet, else Opus), find cited pages.

Mechanical mode returns the candidate pages with [[links]] and source citations
(no LLM text). With Claude available, the chosen model composes the prose answer;
Jev selects the model but never replaces the writing model.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from .config import Config
from .frontmatter import parse
from .index_build import one_line_summary
from .jev_client import JevClient
from .utils import read_text, token_set

__all__ = ["Answer", "answer_question"]


@dataclass
class Answer:
    question: str
    model: str
    choice: str
    confidence: float
    source: str
    pages: list[tuple[str, str, str]] = field(default_factory=list)  # (link, title, summary)

    def as_markdown(self) -> str:
        head = (f"**Roteamento:** Jev({self.source}) -> {self.choice} "
                f"(conf {self.confidence}) -> **{self.model}**")
        if not self.pages:
            return head + "\n\n_Nenhuma página correspondente na wiki ainda._"
        rows = "\n".join(f"- [[{link}|{title}]] — {summ}" for link, title, summ in self.pages)
        return head + ("\n\n**Páginas relevantes (verifique a fonte original antes de "
                       "confiar):**\n\n") + rows


def _candidate_pages(cfg: Config, question: str, top: int = 5) -> list[tuple[str, str, str]]:
    wiki = cfg.path("vault.wiki_dir", "wiki")
    q = token_set(question)
    scored: list[tuple[float, str, str, str]] = []
    for path in wiki.rglob("*.md"):
        stem = path.stem.lower()
        if stem in ("index", "log"):
            continue
        meta, body = parse(read_text(path))
        overlap = len(q & token_set(body + " " + (meta.get("title") or "")))
        if overlap:
            rel = str(path.relative_to(wiki)).replace("\\", "/")[:-3]  # drop .md
            scored.append((overlap, rel, meta.get("title") or stem, one_line_summary(body)))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [(r, t, s) for _, r, t, s in scored[:top]]


def answer_question(cfg: Config, question: str, db=None) -> Answer:
    index_text = read_text(cfg.path("vault.wiki_dir", "wiki") / "index.md")
    jev = JevClient(cfg, db=db)
    route = jev.route_question(question, index_text)
    pages = _candidate_pages(cfg, question)
    return Answer(
        question=question, model=route.model, choice=route.choice,
        confidence=route.confidence, source=route.source, pages=pages,
    )
