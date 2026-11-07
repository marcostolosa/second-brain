"""Acceptance #1/#2/#8/#10: end-to-end ingest, dedupe idempotency, resume."""

from secondbrain.capture import capture_link
from secondbrain.db import VaultDB
from secondbrain.models import Status
from secondbrain.pipeline import run_inbox
from secondbrain.twitter import TweetResult

TWEET = "https://x.com/mr_buzzoni/status/2115443090068516935"


def _fake_tweet(_id, _cfg):
    return TweetResult(
        id="2115443090068516935", url=TWEET, author_name="Buzzoni",
        author_screen_name="mr_buzzoni",
        text="LLM wiki built with claude, obsidian and jev router",
        created_at="2026-10-28", raw_json=b'{"raw":1}',
    )


def test_end_to_end_tweet_ingest(vault, monkeypatch):
    monkeypatch.setattr("secondbrain.pipeline.fetch_tweet", _fake_tweet)
    monkeypatch.setattr("secondbrain.pipeline.fetch_thread", _fake_tweet)

    capture_link(vault, TWEET, title="buzzoni llm wiki")
    with VaultDB(vault) as db:
        s1 = run_inbox(vault, db)
        assert s1.discovered == 1
        assert s1.done == 1
        # source page written, index + log updated
        sources = list((vault.root / "wiki" / "sources").glob("*.md"))
        assert len(sources) == 1
        assert "2115443090068516935" not in sources[0].name  # slug, not raw id
        assert (vault.root / "wiki" / "index.md").exists()
        assert (vault.root / "wiki" / "log.md").exists()
        # raw JSON kept immutable
        assert (vault.root / "raw" / "archive" / "tweet-2115443090068516935.json").exists()

        # idempotent: second run discovers nothing, creates no new pages
        s2 = run_inbox(vault, db)
        assert s2.discovered == 0
        assert len(list((vault.root / "wiki" / "sources").glob("*.md"))) == 1


def test_duplicate_url_with_tracking_is_deduped(vault, monkeypatch):
    monkeypatch.setattr("secondbrain.pipeline.fetch_tweet", _fake_tweet)
    monkeypatch.setattr("secondbrain.pipeline.fetch_thread", _fake_tweet)

    capture_link(vault, TWEET + "?s=20&utm_source=a", title="buzzoni llm wiki")
    capture_link(vault, TWEET + "?t=zzz&utm_campaign=b", title="buzzoni llm wiki")
    with VaultDB(vault) as db:
        s = run_inbox(vault, db)
        assert s.discovered == 2
        assert s.done == 1
        assert s.duplicates == 1
        # exactly one source page despite two captures
        assert len(list((vault.root / "wiki" / "sources").glob("*.md"))) == 1


def test_resume_after_interruption(vault, monkeypatch):
    """An item left mid-flight (fetching) resumes cleanly on the next run."""
    monkeypatch.setattr("secondbrain.pipeline.fetch_tweet", _fake_tweet)
    monkeypatch.setattr("secondbrain.pipeline.fetch_thread", _fake_tweet)
    capture_link(vault, TWEET, title="buzzoni llm wiki")
    with VaultDB(vault) as db:
        from secondbrain.pipeline import register_new_inbox
        items = register_new_inbox(vault, db)
        # simulate a crash right after moving to FETCHING
        db.set_status(items[0], Status.FETCHING.value, "simulated crash point")
    # new DB connection (as if process restarted)
    with VaultDB(vault) as db:
        s = run_inbox(vault, db)
        assert s.done == 1
        assert db.get(items[0].id).status == Status.DONE.value
