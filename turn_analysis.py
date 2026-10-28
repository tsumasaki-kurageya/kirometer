"""Read-only turn-level metering analysis for Kiro CLI JSON metadata."""
from __future__ import annotations

import json
import math
from collections import Counter
from pathlib import Path


def credit_rows(data: dict) -> list[dict]:
    """Return one row per user turn, including missing-usage rows."""
    metadata = (data.get("session_state") or {}).get("conversation_metadata") or {}
    turns = metadata.get("user_turn_metadatas") or []
    if not isinstance(turns, list):
        return []
    rows = []
    for index, turn in enumerate(turns, 1):
        usages = turn.get("metering_usage", []) if isinstance(turn, dict) else []
        total = 0.0
        recorded = False
        if isinstance(usages, list):
            for entry in usages:
                if not isinstance(entry, dict) or str(entry.get("unit", "")).lower() not in ("credit", "credits"):
                    continue
                try:
                    value = float(entry.get("value"))
                except (ValueError, TypeError):
                    continue
                if math.isfinite(value) and value >= 0:
                    total += value
                    recorded = True
        rows.append({"turn": index, "credits": round(total, 6) if recorded else None})
    return rows


def session_turns(root: Path, session_id: str) -> list[dict]:
    """Load only a metadata JSON whose filename matches a known session ID."""
    if not session_id or "/" in session_id or "\\" in session_id or session_id in (".", ".."):
        return []
    path = root / (session_id + ".json")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    if not isinstance(data, dict) or str(data.get("session_id", session_id)) != session_id:
        return []
    return credit_rows(data)


def parent_diagnostics(sessions: list) -> dict:
    """Flag parent/child relationships; no unverified automatic deduction."""
    ids = {s.session_id for s in sessions}
    children = [s for s in sessions if s.parent_session_id]
    pairs = [s for s in children if s.parent_session_id in ids]
    return {
        "child_sessions": len(children),
        "linked_children": len(pairs),
        "linked_with_credits": sum(s.credits is not None for s in pairs),
        "linked_credit_sum": round(sum(s.credits or 0 for s in pairs), 6),
    }
