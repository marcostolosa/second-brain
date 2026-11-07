"""Prompt-injection defense for untrusted source content.

Source text is DATA, never instructions (CLAUDE.md §2). This module adds a
mechanical layer on top of that contract:

  * ``scan`` detects injection-shaped patterns (PT + EN) and suspicious payloads.
  * ``strip_invisible`` removes zero-width / bidi / control characters used to
    smuggle hidden instructions past a human reader.
  * ``fence_untrusted`` wraps content so that, when an agent later reads the
    source page, the text cannot act as Markdown/instructions: headings,
    ``[[wikilinks]]``, fake tool calls and callouts inside it stay inert.

Nothing is deleted from the meaning of the source — content is preserved as data,
only neutralized and flagged. Detection never blocks ingestion of public material
on its own; it raises visibility (report + frontmatter) and, combined with the
sensitivity policy, can route an item to ``needs_review``.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

__all__ = ["ScanResult", "scan", "strip_invisible", "fence_untrusted", "neutralize_for_page"]

# Injection-shaped phrases, bilingual. Kept broad on purpose; these only FLAG.
_PATTERNS: dict[str, re.Pattern] = {
    "ignore_previous": re.compile(
        r"(?i)\b(ignore|disregard|forget|esque[çc]a|desconsidere)\b[^.\n]{0,40}"
        r"\b(previous|above|prior|anterior(?:es)?|acima|todas as|"
        r"instruction|instru[çc][õo]es|prompt|regras?|rules?)\b"),
    "new_instructions": re.compile(
        r"(?i)\b(new instructions?|novas instru[çc][õo]es|from now on|a partir de agora|"
        r"you are now|agora voc[êe] [ée]|act as|aja como|pretend to be|finja ser)\b"),
    "system_prompt": re.compile(
        r"(?i)\b(system prompt|developer mode|modo desenvolvedor|jailbreak|DAN mode|"
        r"prompt do sistema|sua instru[çc][ãa]o de sistema)\b"),
    "reveal_secrets": re.compile(
        r"(?i)\b(reveal|print|show|envie?|send|exfiltrate|vaze|leak|mostre|imprima)\b"
        r"[^.\n]{0,40}\b(\.env|api[-_ ]?key|token|secret|senha|password|credential)\b"),
    "run_command": re.compile(
        r"(?i)\b(run|execute|rode|execute|invoke|chame)\b[^.\n]{0,30}"
        r"\b(powershell|cmd|bash|sh|python|curl|wget|Invoke-WebRequest|rm\s+-rf|del\s)\b"),
    "read_path": re.compile(
        r"(?i)\b(read|open|cat|leia|abra)\b[^.\n]{0,20}"
        r"(\.\./|\.env|id_rsa|credential|\\state\\|/state/)"),
    "tool_or_rule_edit": re.compile(
        r"(?i)\b(CLAUDE\.md|settings\.json|allowedTools|permission-mode|always allow|"
        r"sempre permitir|--dangerously-skip-permissions)\b"),
    "url_to_ip": re.compile(r"https?://(\d{1,3}\.){3}\d{1,3}"),
    "data_exfil_url": re.compile(r"(?i)\b(POST|GET|fetch|curl|wget)\b[^.\n]{0,30}https?://"),
}

# Zero-width, bidi-override and control characters (minus \t \n \r).
_INVISIBLE = re.compile(
    "[​‌‍‎‏‪‫‬‭‮"
    "⁠⁡⁢⁣⁤﻿­]"
    "|[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]"
)


@dataclass
class ScanResult:
    hits: list[str]
    invisible_chars: int

    @property
    def flagged(self) -> bool:
        return bool(self.hits) or self.invisible_chars > 0


def scan(text: str) -> ScanResult:
    hits = [name for name, rx in _PATTERNS.items() if rx.search(text)]
    invisible = len(_INVISIBLE.findall(text))
    return ScanResult(hits=sorted(hits), invisible_chars=invisible)


def strip_invisible(text: str) -> str:
    return _INVISIBLE.sub("", text)


def fence_untrusted(text: str) -> str:
    """Wrap text in a code fence long enough that no inner backtick run escapes it,
    so headings/wikilinks/fake tool-calls inside stay inert when rendered/read."""
    longest = 0
    for run in re.findall(r"`+", text):
        longest = max(longest, len(run))
    fence = "`" * max(3, longest + 1)
    return f"{fence}text\n{text}\n{fence}"


def neutralize_for_page(text: str) -> tuple[str, ScanResult]:
    """Count invisibles on the original, scan the cleaned text, fence the cleaned.

    Invisibles are counted before stripping (that is the signal); pattern matching
    runs on the cleaned text so hidden characters can't split keywords.
    """
    invisible = len(_INVISIBLE.findall(text))
    cleaned = strip_invisible(text)
    patt = scan(cleaned)
    result = ScanResult(hits=patt.hits, invisible_chars=invisible)
    return fence_untrusted(cleaned), result
