# kirometer 📊

Local-first Kiro CLI credit dashboard. Reads session JSON metadata only; no prompts, chat messages, or tool output are uploaded.

## Quick start (WSL / Linux)

Requires Python 3.10+.

```bash
git clone https://github.com/tsumasaki-kurageya/kirometer.git
cd kirometer
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

Open http://localhost:8501 in your browser. For the unmerged feature branch use `git switch feat/phase1-dashboard` **before** installing requirements.

## Dashboard

- Recorded credit totals, session counts, average and metadata coverage
- Last 7 days / 30 days / all time (session creation date, Asia/Tokyo)
- Daily trends and per-directory project credits
- Highest-cost sessions, title search, drill-down, CSV export
- Sidebar refresh button

## Source and limitations

Reads `~/.kiro/sessions/cli/*.json` (Kiro CLI 2.35.1 shape).
Sums `session_state.conversation_metadata.user_turn_metadatas[].metering_usage[]` entries whose `unit` is `credit`.
Missing metering is unknown, not zero. Values may not match Kiro billing.
Projects use basename of `cwd` (worktrees may be separate), parent-child usage may overlap.
SQLite/JSONL are **not** read in Phase 1. Session titles/paths can be sensitive; CSV exports should not be committed.

## Run unit tests

```bash
python3 -m unittest discover -s tests -v
```

## Multiple local history sources (Phase 3)

In the sidebar, enter extra `cli` session directories, one per line. For example,
a read-only copy from another WSL environment or Mac.

- Local metadata JSON is read directly. No uploads or automatic copying.
- Matching `session_id` values are counted only once. A record with credit
  metering is preferred; if both have the same metering availability, the
  newer updated record is used.
- The source path of the selected record determines where the optional
  prompt preview is loaded from.
- Missing folders and duplicate session IDs are counted in the sidebar.
- Model snapshot counts honor the deduplicated session selection.
- The detailed data-quality audit currently inspects the primary directory only.

This is **multi-directory reading**, not scheduled ingestion or durable storage.
Source folders must remain available. Copying conversation/session files can
expose confidential content: keep any imported copies local and access-controlled.

Run `python3 -m unittest discover -s tests -v` to verify parsing/deduplication.
