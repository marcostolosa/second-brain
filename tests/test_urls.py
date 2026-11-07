"""Acceptance #1 (ID/URL), #2 (tracking idempotency), SSRF guard."""

import pytest

from secondbrain.urls import normalize_url, strip_tracking, tweet_id, assert_public_http_url, SsrfError

TWEET = "https://x.com/mr_buzzoni/status/2115443090068516935"


def test_tweet_id_and_normalization():
    u = normalize_url(TWEET + "?s=20&t=abc&utm_source=newsletter")
    assert u == TWEET
    assert tweet_id(u) == "2115443090068516935"


def test_tracking_params_stripped_consistently():
    a = normalize_url("https://ex.com/post?utm_source=x&id=7&fbclid=zz")
    b = normalize_url("https://ex.com/post?id=7")
    assert a == b  # idempotent canonical form


def test_fxtwitter_and_variants_extract_same_id():
    for host in ("x.com", "twitter.com", "fxtwitter.com", "fixupx.com"):
        assert tweet_id(f"https://{host}/u/status/2115443090068516935") == "2115443090068516935"


@pytest.mark.parametrize("bad", [
    "http://127.0.0.1/x", "http://localhost:8080", "http://169.254.169.254/latest",
    "http://10.0.0.5", "http://192.168.1.1", "file:///etc/passwd", "ftp://host/x",
])
def test_ssrf_blocks_private_and_bad_schemes(bad):
    with pytest.raises(SsrfError):
        assert_public_http_url(bad)


def test_ssrf_allows_public():
    # public DNS name resolves to public IPs (skip if offline, e.g. in CI sandbox)
    try:
        assert assert_public_http_url("https://api.fxtwitter.com/2/status/1")
    except SsrfError as e:
        if "DNS resolution failed" in str(e):
            pytest.skip("no network for DNS resolution")
        raise
