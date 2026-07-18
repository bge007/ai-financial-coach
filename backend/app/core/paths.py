"""Resolve versioned YAML under config/ in local and Docker layouts."""

from __future__ import annotations

from pathlib import Path


def config_dir() -> Path:
    here = Path(__file__).resolve()
    candidates = [
        here.parents[3] / "config",  # repo root when running from backend/app/...
        Path("/app/config"),  # docker compose mount
        Path.cwd() / "config",
        here.parents[2] / "config",
    ]
    for path in candidates:
        if path.is_dir():
            return path
    return candidates[0]


def config_path(*parts: str) -> Path:
    return config_dir().joinpath(*parts)
