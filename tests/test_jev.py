"""Acceptance #13 (routing) and #4 (Jev offline fallback)."""

import requests

from secondbrain.jev_client import JevClient


def test_lookup_routes_to_sonnet(vault):
    jev = JevClient(vault)
    index = "scout haiku model librarian opus model jev router dedupe"
    v = jev.route_question("what is the scout haiku model", index)
    assert v.choice == "lookup"
    assert v.confidence >= 0.85
    assert v.model == "sonnet"
    assert v.source == "mock"


def test_synthesis_routes_to_opus(vault):
    jev = JevClient(vault)
    v = jev.route_question("compare scout vs librarian tradeoffs and synthesize", "scout librarian")
    assert v.model == "opus"


def test_dedupe_identical_is_duplicate(vault):
    jev = JevClient(vault)
    text = "mr buzzoni llm wiki claude obsidian jev scout librarian architecture"
    v = jev.dedupe(text, text)
    assert v.verdict == "duplicate"
    assert v.score >= 0.9


def test_dedupe_distinct_is_new(vault):
    jev = JevClient(vault)
    v = jev.dedupe("completely different topic about gardening tomatoes", "llm wiki claude jev")
    assert v.verdict == "new"


def test_live_without_token_stays_mock(vault, monkeypatch):
    monkeypatch.setenv("JEV_MODE", "live")  # but no token configured
    from secondbrain.config import load_config
    cfg = load_config(vault.root)
    jev = JevClient(cfg)
    assert jev.mode == "mock"


def test_live_network_failure_falls_back_to_opus(vault, monkeypatch):
    monkeypatch.setenv("JEV_MODE", "live")
    monkeypatch.setenv("TYPESAFE_API_TOKEN", "test-token")
    from secondbrain.config import load_config
    cfg = load_config(vault.root)

    def boom(*a, **k):
        raise requests.ConnectionError("no network")

    monkeypatch.setattr("secondbrain.jev_client.requests.post", boom)
    jev = JevClient(cfg)
    jev.max_retries, jev.backoff = 1, 0.0  # keep the test fast; no real backoff waits
    assert jev.mode == "live"
    v = jev.route_question("what is x", "y")
    assert "fallback" in v.source
    assert v.model == "opus"  # conservative fallback
