"""Acceptance #10: sensitive-data policy + redaction."""

from secondbrain.policy import load_policy


def test_high_risk_blocks_auto_and_external(vault):
    pol = load_policy(vault.root)
    d = pol.classify(url=None, text="This is a confidential client engagement; password: hunter2")
    assert d.risk == "high"
    assert d.auto_ingest is False
    assert d.allow_sync is False
    assert d.allow_jev is False


def test_low_risk_allows(vault):
    pol = load_policy(vault.root)
    d = pol.classify(url="https://x.com/a/status/1", text="a neutral public note about rust")
    assert d.risk == "low"
    assert d.auto_ingest and d.allow_sync and d.allow_jev


def test_redaction_strips_secrets(vault):
    pol = load_policy(vault.root)
    red = pol.redact("api_key: ABCD1234\nAuthorization: Bearer xyztoken\nhello")
    assert "ABCD1234" not in red
    assert "xyztoken" not in red
    assert "hello" in red
