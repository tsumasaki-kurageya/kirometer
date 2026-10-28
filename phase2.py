"""Phase 2: privacy-conscious analysis of tool events and worktree paths.

Only tool *arguments* are inspected in memory to identify SKILL.md references.
Never persist or display raw commands, prompts or tool results.
"""
from __future__ import annotations
import json
import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

SKILL_PATH = re.compile(r"(?i)(?:[\w.~-]+[/\\])*([\w.-]+)[/\\]SKILL\.md\b")
GENERIC_SKILL = re.compile(r"(?i)\bSKILL\.md\b")

@dataclass
class SkillEvidence:
    # Tool invocation is evidence of attempted access, NOT proof of activation.
    read_calls: int = 0
    shell_calls: int = 0
    named_skills: Counter = field(default_factory=Counter)

    @property
    def status(self) -> str:
        return "Skillファイル操作候補" if self.read_calls + self.shell_calls else "確認できず"

def project_name(cwd: str, normalize_worktrees: bool = True) -> str:
    if not cwd:
        return "(不明)"
    parts = Path(cwd).parts
    if normalize_worktrees:
        for i, part in enumerate(parts):
            # E.g. /home/user/dk-connect-bm.worktrees/main/
            if part.endswith(".worktrees"):
                return part[:-len(".worktrees")]
            # E.g. /project/.git/worktrees/main is a git metadata directory
            if part == "worktrees" and i > 0 and parts[i-1] == ".git":
                return parts[i-2] if i >= 2 else "(不明)"
    return Path(cwd).name

def _tool_calls(value: Any):
    if isinstance(value, dict):
        name = value.get("name")
        if name in ("read", "shell"):
            args = value.get("input", value.get("args", {}))
            yield name, args
        for child in value.values():
            if isinstance(child, (dict, list)):
                yield from _tool_calls(child)
    elif isinstance(value, list):
        for child in value:
            yield from _tool_calls(child)

def scan_session_jsonl(path: Path) -> SkillEvidence:
    evidence = SkillEvidence()
    if not path.exists():
        return evidence
    try:
        with path.open(encoding="utf-8", errors="replace") as stream:
            for line in stream:
                try:
                    event = json.loads(line)
                except ValueError:
                    continue
                if not isinstance(event, dict) or event.get("kind") != "AssistantMessage":
                    continue
                data = event.get("data", {})
                for tool, args in _tool_calls(data):
                    # These are tool-call inputs. They may describe editing or
                    # searching a Skill, not necessarily loading/activating it.
                    raw = json.dumps(args, ensure_ascii=False) if not isinstance(args, str) else args
                    if not GENERIC_SKILL.search(raw):
                        continue
                    if tool == "read":
                        evidence.read_calls += 1
                    else:
                        evidence.shell_calls += 1
                    for skill in set(SKILL_PATH.findall(raw)):
                        evidence.named_skills[skill] += 1
    except OSError:
        pass
    return evidence

def load_skill_evidence(root: Path, session_ids: set[str]) -> dict[str, SkillEvidence]:
    # Only read files matching known metadata sessions. No search of other user files.
    return {sid: scan_session_jsonl(root / (sid + ".jsonl")) for sid in session_ids}
