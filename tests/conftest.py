"""Shared pytest fixtures: an isolated temp vault per test."""

from __future__ import annotations

import os
import shutil
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture()
def vault(tmp_path, monkeypatch):
    """Create an isolated vault under tmp_path and point the package at it."""
    root = tmp_path / "SecondBrain"
    for d in ["raw/inbox", "raw/assets", "raw/archive",
              "wiki/sources", "wiki/entities", "wiki/concepts", "wiki/questions",
              "state", "logs", "reports/history", "config", "templates"]:
        (root / d).mkdir(parents=True, exist_ok=True)
    # a pyproject marker so find_vault_root also works without the env var
    (root / "pyproject.toml").write_text("[project]\nname='secondbrain-test'\n", encoding="utf-8")
    # reuse the real config so policy patterns match production
    for name in ("config.example.yaml", "source-policy.yaml"):
        src = REPO_ROOT / "config" / name
        if src.exists():
            shutil.copy2(src, root / "config" / name)

    monkeypatch.setenv("SECONDBRAIN_ROOT", str(root))
    monkeypatch.setenv("JEV_MODE", "mock")
    monkeypatch.delenv("TYPESAFE_API_TOKEN", raising=False)

    from secondbrain.config import load_config
    return load_config(root)
