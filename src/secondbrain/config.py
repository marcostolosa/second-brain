"""Configuration loading: config.yaml (falls back to config.example.yaml) + env.

Secrets never live in config files: the Jev token is read from the environment or
Windows Credential Manager (see secrets.py), never from YAML.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml

from .paths import find_vault_root

__all__ = ["Config", "load_config"]


class Config:
    """Thin wrapper over the config dict with dotted-path access."""

    def __init__(self, data: dict[str, Any], root: Path):
        self._d = data
        self.root = root

    def get(self, dotted: str, default: Any = None) -> Any:
        node: Any = self._d
        for part in dotted.split("."):
            if isinstance(node, dict) and part in node:
                node = node[part]
            else:
                return default
        return node

    @property
    def data(self) -> dict[str, Any]:
        return self._d

    # Convenience accessors used across the pipeline -----------------------
    def path(self, dotted: str, default: str) -> Path:
        return self.root / self.get(dotted, default)

    @property
    def jev_mode(self) -> str:
        return os.environ.get("JEV_MODE") or self.get("jev.mode", "mock")

    @property
    def jev_url(self) -> str:
        return os.environ.get("JEV_API_URL") or self.get(
            "jev.api_url", "https://api.typesafe.ai/v1/systemone"
        )

    @property
    def jev_model(self) -> str:
        return os.environ.get("JEV_MODEL") or self.get("jev.model", "jev-latest")


def load_config(root: Path | None = None) -> Config:
    root = (root or find_vault_root()).resolve()
    cfg_dir = root / "config"
    real = cfg_dir / "config.yaml"
    example = cfg_dir / "config.example.yaml"
    src = real if real.exists() else example

    data: dict[str, Any] = {}
    if src.exists():
        with open(src, "r", encoding="utf-8") as fh:
            data = yaml.safe_load(fh) or {}

    # Load .env (simple KEY=VALUE) into os.environ if present and not already set.
    env_file = root / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            os.environ.setdefault(k.strip(), v.strip())

    return Config(data, root)
