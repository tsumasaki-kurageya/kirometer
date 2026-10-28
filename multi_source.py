"""Load local Kiro session metadata from multiple folders without double counting.

Duplicate session IDs are resolved deterministically: prefer a record with
metering, then latest updated_at, then the first configured source.
Only metadata JSON is read. Nothing is copied or persisted.
"""
from __future__ import annotations
from collections import Counter
from pathlib import Path
from kirometer import load_sessions, Session


def parse_roots(primary: Path, extra: str) -> list[Path]:
    paths = [primary, *(Path(line.strip()).expanduser() for line in extra.splitlines() if line.strip())]
    unique = []
    seen = set()
    for path in paths:
        canonical = path.expanduser().resolve()
        if canonical not in seen:
            unique.append(canonical)
            seen.add(canonical)
    return unique


def load_multiple(roots: list[Path]) -> tuple[list[Session], dict[str, Path], Counter]:
    chosen: dict[str, tuple[Session, Path, int]] = {}
    stats: Counter = Counter()
    for index, root in enumerate(roots):
        if not root.is_dir():
            stats["missing_sources"] += 1
            continue
        sessions, diag = load_sessions(root)
        stats["files"] += diag["files"]
        stats["invalid"] += diag["invalid"]
        for session in sessions:
            stats["observed_sessions"] += 1
            key = session.session_id
            candidate = (session, root, index)
            old = chosen.get(key)
            if old is None:
                chosen[key] = candidate
                continue
            stats["duplicate_sessions"] += 1
            previous = old[0]
            # Prefer known credit information. Do not add duplicate totals.
            new_score = (session.credits is not None, session.updated_at is not None, session.updated_at or session.created_at or 0)
            old_score = (previous.credits is not None, previous.updated_at is not None, previous.updated_at or previous.created_at or 0)
            # Avoid comparison between datetime and numeric in final tuple.
            if new_score[:2] > old_score[:2] or (new_score[:2] == old_score[:2] and
                (session.updated_at or session.created_at) is not None and
                (previous.updated_at or previous.created_at) is not None and
                (session.updated_at or session.created_at) > (previous.updated_at or previous.created_at)):
                chosen[key] = candidate
    stats["loaded"] = len(chosen)
    stats["with_credit"] = sum(s.credits is not None for s, _, _ in chosen.values())
    stats["without_credit"] = stats["loaded"] - stats["with_credit"]
    sessions = [record[0] for record in chosen.values()]
    locations = {sid: record[1] for sid, record in chosen.items()}
    return sessions, locations, stats
