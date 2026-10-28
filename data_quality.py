"""Non-sensitive schema diagnostics for local Kiro CLI metadata.

Only structural field names and coverage counts are reported. No user prompts,
tool arguments, paths, model names or arbitrary values are exported.
"""
from __future__ import annotations

import json
import math
from collections import Counter
from pathlib import Path

MODEL_KEYS = {"model", "model_id", "model_name", "modelId", "modelName"}


def audit_metadata(root: Path) -> dict:
    result = Counter()
    model_locations = Counter()
    for path in root.glob("*.json"):
        result["files"] += 1
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                raise ValueError("Not an object")
        except (OSError, ValueError):
            result["unreadable"] += 1
            continue
        state = data.get("session_state")
        state = state if isinstance(state, dict) else {}
        metadata = state.get("conversation_metadata")
        metadata = metadata if isinstance(metadata, dict) else {}
        turns = metadata.get("user_turn_metadatas")
        if not isinstance(turns, list):
            result["no_turn_array"] += 1
            turns = []
        if not turns:
            result["no_turns"] += 1
        valid_credits = 0
        for turn in turns:
            result["turns"] += 1
            if not isinstance(turn, dict):
                result["invalid_turn"] += 1
                continue
            for name in MODEL_KEYS.intersection(turn):
                model_locations[f"turn.{name}"] += 1
            usages = turn.get("metering_usage")
            if not isinstance(usages, list):
                result["no_metering_array"] += 1
                continue
            per_turn_valid = False
            for item in usages:
                if not isinstance(item, dict):
                    continue
                for name in MODEL_KEYS.intersection(item):
                    model_locations[f"metering_usage.{name}"] += 1
                if str(item.get("unit", "")).lower() not in ("credit", "credits"):
                    continue
                try:
                    value = float(item.get("value"))
                except (TypeError, ValueError):
                    continue
                if math.isfinite(value) and value >= 0:
                    per_turn_valid = True
            if per_turn_valid:
                valid_credits += 1
                result["metered_turns"] += 1
            else:
                result["unmetered_turns"] += 1
        if valid_credits:
            result["metered_sessions"] += 1
        else:
            result["unmetered_sessions"] += 1
        for name in MODEL_KEYS.intersection(state):
            model_locations[f"session_state.{name}"] += 1
        model_state = state.get("rts_model_state")
        if isinstance(model_state, dict):
            for name in MODEL_KEYS.intersection(model_state):
                model_locations[f"rts_model_state.{name}"] += 1
    return {"counts": dict(result), "model_fields": dict(sorted(model_locations.items()))}
