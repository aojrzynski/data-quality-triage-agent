"""Configuration helpers for the project."""

from __future__ import annotations

import json
from pathlib import Path

from src.models import AgentConfig


DEFAULT_CONFIG_PATH = Path("config/default_config.json")


def load_agent_config(path: str | Path | None = None) -> AgentConfig:
    """Load the agent configuration from JSON.

    If no path is provided, the default project config is used.
    """
    config_path = Path(path) if path else DEFAULT_CONFIG_PATH

    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with config_path.open("r", encoding="utf-8") as f:
        payload = json.load(f)

    return AgentConfig.from_dict(payload)