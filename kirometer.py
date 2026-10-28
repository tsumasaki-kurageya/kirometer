"""Read-only Kiro CLI session metadata and credit summaries."""
from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DEFAULT_ROOT = Path.home() / ".kiro" / "sessions" / "cli"


@dataclass(frozen=True)
class Session:
    session_id: str
    title: str
    cwd: str
    created_at: datetime | None
    updated_at: datetime | None
    credits: float | None
    turns: int
    parent_session_id: str | None

    @property
    def project(self) -> str:
        return Path(self.cwd).name if self.cwd else "(unknown)"


def parse_date(value: Any) -> datetime | None:
    if isinstance(value, (int, float)):
        # Some versions use millisecond timestamps.
        seconds = value / 1000 if abs(value) > 1e11 else value
        try:
            return datetime.fromtimestamp(seconds, tz=timezone.utc)
        except (ValueError, OverflowError, OSError):
            return None
    if isinstance(value, str) and value:
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00")).replace(
                tzinfo=timezone.utc
            ) if datetime.fromisoformat(value.replace("Z", "+00:00")).tzinfo is None else datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    return None


def extract_credits(data: dict[str, Any]) -> tuple[float | None, int]:
    metadata = data.get("session_state", {}).get("conversation_metadata", {})
    turns = metadata.get("user_turn_metadatas", [])
    if not isinstance(turns, list):
        return None, 0
    total = 0.0
    found = False
    for turn in turns:
        if not isinstance(turn, dict):
            continue
        usages = turn.get("metering_usage", [])
        if not isinstance(usages, list):
            continue
        for usage in usages:
            if not isinstance(usage, dict) or str(usage.get("unit", "")).lower() not in ("credit", "credits"):
                continue
            try:
                total += float(usage.get("value", 0))
                found = True
            except (ValueError, TypeError):
                continue
    return (round(total, 6) if found else None), len(turns)


def load_sessions(root: Path = DEFAULT_ROOT) -> tuple[list[Session], Counter]:
    sessions: list[Session] = []
    diagnostics: Counter = Counter()
    for path in sorted(root.glob("*.json")):
        diagnostics["files"] += 1
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                diagnostics["invalid"] += 1
                continue
            credits, turns = extract_credits(data)
            if credits is None:
                diagnostics["without_credit"] += 1
            sessions.append(Session(
                session_id=str(data.get("session_id") or path.stem),
                title=str(data.get("title") or "(untitled)"),
                cwd=str(data.get("cwd") or ""),
                created_at=parse_date(data.get("created_at")),
                updated_at=parse_date(data.get("updated_at")),
                credits=credits,
                turns=turns,
                parent_session_id=data.get("parent_session_id"),
            ))
        except (OSError, ValueError, TypeError, AttributeError, KeyError):
            diagnostics["invalid"] += 1
    diagnostics["loaded"] = len(sessions)
    diagnostics["with_credit"] = sum(s.credits is not None for s in sessions)
    return sessions, diagnostics
