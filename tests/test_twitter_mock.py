"""Acceptance #1 (metadata) and #4 (deleted/429) for the FxTwitter client."""

import pytest

from secondbrain.twitter import fetch_tweet, TwitterError


class FakeResp:
    def __init__(self, status, payload=None, content=b"{}"):
        self.status_code = status
        self._p = payload
        self.content = content
        self.text = ""

    def json(self):
        return self._p


def _patch(monkeypatch, resp):
    monkeypatch.setattr("secondbrain.twitter.requests.get", lambda *a, **k: resp)


def test_fetch_tweet_ok(vault, monkeypatch):
    payload = {"tweet": {"id": "2115443090068516935",
                         "url": "https://x.com/mr_buzzoni/status/2115443090068516935",
                         "author": {"name": "Buzzoni", "screen_name": "mr_buzzoni"},
                         "text": "LLM wiki with claude + obsidian + jev",
                         "created_at": "2026-10-28"}}
    _patch(monkeypatch, FakeResp(200, payload, b'{"raw":1}'))
    t = fetch_tweet("2115443090068516935", vault)
    assert t.author_screen_name == "mr_buzzoni"
    assert "jev" in t.text
    assert t.created_at == "2026-10-28"
    assert t.raw_json == b'{"raw":1}'


def test_deleted_tweet_raises(vault, monkeypatch):
    _patch(monkeypatch, FakeResp(404))
    with pytest.raises(TwitterError) as e:
        fetch_tweet("1", vault)
    assert e.value.kind == "deleted"


def test_rate_limited_raises(vault, monkeypatch):
    _patch(monkeypatch, FakeResp(429))
    with pytest.raises(TwitterError) as e:
        fetch_tweet("1", vault)
    assert e.value.kind == "rate_limited"
