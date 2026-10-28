"""Model snapshot analysis, not per-turn model billing attribution."""
from __future__ import annotations
import json
from collections import Counter
from pathlib import Path

def model_snapshots(root: Path) -> dict:
    counts = Counter()
    metered = Counter()
    total = 0
    for path in root.glob("*.json"):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                continue
            total += 1
            state = data.get("session_state") or {}
            info = (state.get("rts_model_state") or {}).get("model_info")
            model = info.get("model_id") if isinstance(info, dict) else None
            if not isinstance(model, str) or not model.strip():
                model = "記録なし"
            counts[model] += 1
            turns = (state.get("conversation_metadata") or {}).get("user_turn_metadatas") or []
            if isinstance(turns, list) and any(
                isinstance(t, dict) and isinstance(t.get("metering_usage"), list)
                and any(isinstance(u, dict) and str(u.get("unit", "")).lower() in ("credit","credits") and isinstance(u.get("value"), (int,float)) for u in t["metering_usage"])
                for t in turns
            ):
                metered[model] += 1
        except (OSError, ValueError, AttributeError, TypeError):
            continue
    return {"total": total, "counts": dict(counts), "metered": dict(metered)}
