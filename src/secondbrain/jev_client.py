"""Jev (TypeSafe) client — the fast yes/no router for dedupe and model selection.

The spec mandates the REST API (POST {jev.api_url}) with a bearer token, NOT the
Python SDK shown in the article. Default mode is ``mock``: a deterministic,
conservative local fallback that needs no network and never leaks data. ``live``
is used only after the user sets a real token and confirms the endpoint; until
then live status is treated as unvalidated.

Operations:
  * Noul   -> probability a summary duplicates an already-indexed source (0..1).
  * Choice -> pick lookup|synthesis|other for a question (with a confidence).

Conservative fallback rule (matches the original design): anything Jev is unsure
about goes up to Opus; dedupe only drops near-identical items.
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass

import requests

from .config import Config
from .secrets import get_typesafe_token

__all__ = ["JevClient", "JevUnavailable", "DedupeVerdict", "RouteVerdict"]

_WORD = re.compile(r"[a-z0-9]{3,}")
_LOOKUP_STARTERS = (
    "who", "what", "when", "where", "which", "define", "list", "how many",
    "quem", "o que", "qual", "quais", "quando", "onde", "defina", "liste",
)


class JevUnavailable(Exception):
    pass


@dataclass
class DedupeVerdict:
    verdict: str          # "duplicate" | "new"
    score: float
    source: str           # live | mock | mock(fallback)


@dataclass
class RouteVerdict:
    model: str            # "sonnet" | "opus"
    choice: str           # lookup | synthesis | other
    confidence: float
    source: str


class JevClient:
    def __init__(self, cfg: Config, token: str | None = None, db=None):
        self.cfg = cfg
        self.db = db
        self.url = cfg.jev_url
        self.model = cfg.jev_model
        self.token = token if token is not None else get_typesafe_token()
        self.timeout = float(cfg.get("jev.timeout_seconds", 20))
        self.max_retries = int(cfg.get("jev.max_retries", 4))
        self.backoff = float(cfg.get("jev.backoff_base_seconds", 1.5))
        self.daily_budget = int(cfg.get("jev.daily_call_budget", 2000))
        requested = cfg.jev_mode
        # Live requires a token; otherwise silently stay in mock.
        self.mode = "live" if (requested == "live" and self.token) else "mock"
        self.live_unvalidated = requested == "live"

    # ---- public high-level API ------------------------------------------
    def dedupe(self, summary_text: str, index_text: str) -> DedupeVerdict:
        threshold = float(self.cfg.get("dedupe.jev_noul_threshold", 0.90))
        question = "Does `index` already list a page for the same source as `summary`?"
        state = {"summary": summary_text[:20000], "index": index_text[-40000:]}
        score, source = self._noul(state, question)
        verdict = "duplicate" if score >= threshold else "new"
        return DedupeVerdict(verdict=verdict, score=score, source=source)

    def route_question(self, question: str, index_text: str) -> RouteVerdict:
        min_conf = float(self.cfg.get("routing.sonnet_when_lookup_min_confidence", 0.85))
        options = {
            "lookup": "The answer sits on one or two pages listed in index.",
            "synthesis": "It needs 4+ pages, a comparison or a new conclusion.",
            "other": "Anything else.",
        }
        state = {"question": question, "index": index_text[-40000:]}
        choice, confidence, source = self._choice(state, question, options)
        model = "sonnet" if (choice == "lookup" and confidence >= min_conf) else "opus"
        return RouteVerdict(model=model, choice=choice, confidence=confidence, source=source)

    # ---- operation wrappers ---------------------------------------------
    def _noul(self, state: dict, question: str) -> tuple[float, str]:
        if self.mode == "live":
            try:
                data = self._post({"dup": {"op": "noul", "prompt": question}}, state)
                ans = (data.get("answers") or {}).get("dup") or {}
                return float(ans.get("noul", 0.0)), "live"
            except JevUnavailable:
                return self._mock_noul(state), "mock(fallback)"
        return self._mock_noul(state), "mock"

    def _choice(self, state: dict, question: str, options: dict) -> tuple[str, float, str]:
        if self.mode == "live":
            try:
                data = self._post(
                    {"depth": {"op": "choice", "prompt": question, "options": options}}, state
                )
                ans = (data.get("answers") or {}).get("depth") or {}
                return (str(ans.get("choice", "other")), float(ans.get("confidence", 0.0)), "live")
            except JevUnavailable:
                c, conf = self._mock_choice(state)
                return c, conf, "mock(fallback)"
        c, conf = self._mock_choice(state)
        return c, conf, "mock"

    # ---- REST transport --------------------------------------------------
    def _post(self, questions: dict, state: dict) -> dict:
        if not self.token:
            raise JevUnavailable("no token configured")
        if self.db is not None and self.db.usage_today("jev") >= self.daily_budget:
            raise JevUnavailable("daily Jev call budget exhausted")

        payload = {"model": self.model, "state": state, "questions": questions}
        headers = {"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"}
        last_err: Exception | None = None
        for attempt in range(self.max_retries):
            try:
                r = requests.post(self.url, json=payload, headers=headers, timeout=self.timeout)
                if r.status_code == 200:
                    if self.db is not None:
                        self.db.record_usage("jev", calls=1)
                    return r.json()
                if r.status_code in (429,) or r.status_code >= 500:
                    last_err = JevUnavailable(f"HTTP {r.status_code}")
                else:
                    raise JevUnavailable(f"HTTP {r.status_code}: {r.text[:200]}")
            except requests.RequestException as e:
                last_err = e
            time.sleep(self.backoff * (2 ** attempt))
        raise JevUnavailable(f"Jev unreachable after {self.max_retries} tries: {last_err}")

    # ---- deterministic mock ---------------------------------------------
    @staticmethod
    def _tokens(text: str) -> set[str]:
        return set(_WORD.findall(text.lower()))

    def _mock_noul(self, state: dict) -> float:
        """Conservative Jaccard overlap: only near-identical text scores high."""
        a = self._tokens(state.get("summary", ""))
        b = self._tokens(state.get("index", ""))
        if not a:
            return 0.0
        inter = len(a & b)
        union = len(a | b) or 1
        return round(inter / union, 4)

    def _mock_choice(self, state: dict) -> tuple[str, float]:
        """Heuristic depth: short factual questions whose keywords appear in the
        index are 'lookup' with high confidence; otherwise 'synthesis'/'other'
        with low confidence so routing falls back to Opus."""
        q = (state.get("question") or "").strip().lower()
        idx = self._tokens(state.get("index", ""))
        is_short = len(q) <= 140
        starts_lookup = any(q.startswith(s) for s in _LOOKUP_STARTERS)
        qtokens = self._tokens(q)
        overlap = (len(qtokens & idx) / len(qtokens)) if qtokens else 0.0
        if is_short and starts_lookup and overlap >= 0.5:
            return "lookup", round(0.80 + 0.19 * overlap, 4)
        if "compare" in q or "vs" in q or "synthesi" in q or "why" in q or "por que" in q:
            return "synthesis", 0.4
        return "other", 0.3
