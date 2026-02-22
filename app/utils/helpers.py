"""Shared helpers."""
import json
from typing import Any


def safe_json_loads(value: str | None) -> dict | None:
    """Parse JSON string to dict. Return None if invalid or empty."""
    if not value:
        return None
    try:
        out = json.loads(value)
        return out if isinstance(out, dict) else None
    except (json.JSONDecodeError, TypeError):
        return None


def safe_json_dumps(obj: dict | None) -> str | None:
    """Serialize dict to JSON string. Return None if input is None."""
    if obj is None:
        return None
    try:
        return json.dumps(obj)
    except (TypeError, ValueError):
        return None
