"""Keyword router — config-driven, multi-match."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from app.core.paths import config_path

_CONFIG = config_path("agent_routes.yaml")


def load_routes(path: Path | None = None) -> dict[str, Any]:
    return yaml.safe_load((path or _CONFIG).read_text(encoding="utf-8"))


def route_query(query: str, config: dict[str, Any] | None = None) -> list[str]:
    """Return ordered list of agent names. Always at least default coach."""
    cfg = config or load_routes()
    q = (query or "").lower()
    matched: list[str] = []
    for agent, keywords in (cfg.get("routes") or {}).items():
        for kw in keywords or []:
            if str(kw).lower() in q:
                if agent not in matched:
                    matched.append(agent)
                break
    if not matched:
        matched = [cfg.get("default") or "coach_agent"]
    return matched
