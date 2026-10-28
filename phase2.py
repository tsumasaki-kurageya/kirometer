"""Project name normalization for Kiro CLI session paths."""
from pathlib import Path

def project_name(cwd: str, normalize_worktrees: bool = True) -> str:
    if not cwd:
        return "(不明)"
    parts = Path(cwd).parts
    if normalize_worktrees:
        for i, part in enumerate(parts):
            if part.endswith(".worktrees"):
                return part[:-len(".worktrees")]
            if part == "worktrees" and i > 1 and parts[i - 1] == ".git":
                return parts[i - 2]
    return Path(cwd).name
