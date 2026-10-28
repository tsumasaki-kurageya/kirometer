"""Streamlit dashboard for local Kiro CLI sessions."""
from __future__ import annotations

import csv
import io
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import streamlit as st

from kirometer import DEFAULT_ROOT, load_sessions

st.set_page_config(page_title="kirometer", page_icon="📊", layout="wide")
st.title("📊 kirometer")
st.caption("Kiro CLI credit usage · local, read-only · recorded credits only")

root_input = st.sidebar.text_input("Session directory", value=str(DEFAULT_ROOT))
root = Path(root_input).expanduser()
if not root.is_dir():
    st.error(f"Directory not found: {root}")
    st.stop()

@st.cache_data(ttl=60, show_spinner=False)
def get_data(directory: str):
    return load_sessions(Path(directory))

sessions, diagnostics = get_data(str(root))
if st.sidebar.button("Refresh data"):
    get_data.clear()
    st.rerun()

st.sidebar.caption(f"Parsed {diagnostics['loaded']} / {diagnostics['files']} files · {diagnostics['invalid']} invalid")
st.sidebar.caption(f"{diagnostics['with_credit']} with recorded credits · {diagnostics['without_credit']} without")

rows = []
for s in sessions:
    rows.append({
        "session_id": s.session_id,
        "title": s.title,
        "project": s.project,
        "cwd": s.cwd,
        "created_at": s.created_at,
        "updated_at": s.updated_at,
        "credits": s.credits,
        "turns": s.turns,
        "parent_session_id": s.parent_session_id,
    })
if not rows:
    st.warning("No session metadata found.")
    st.stop()

df = pd.DataFrame(rows)
for col in ("created_at", "updated_at"):
    df[col] = pd.to_datetime(df[col], utc=True, errors="coerce").dt.tz_convert("Asia/Tokyo")
df["date"] = df["created_at"].dt.date

period = st.sidebar.selectbox("Period (created date, JST)", ["All time", "Last 7 days", "Last 30 days"])
if period != "All time":
    days = 7 if period == "Last 7 days" else 30
    cutoff = datetime.now().astimezone().date() - timedelta(days=days - 1)
    df = df[df["date"] >= cutoff]

project_names = sorted(df["project"].unique().tolist())
selected = st.sidebar.multiselect("Projects (directory names)", project_names, default=project_names)
df = df[df["project"].isin(selected)]

search = st.sidebar.text_input("Search title")
if search:
    df = df[df["title"].str.contains(search, case=False, regex=False, na=False)]

with_credit = df[df["credits"].notna()].copy()
total = with_credit["credits"].sum()
c1, c2, c3, c4 = st.columns(4)
c1.metric("Recorded credits", f"{total:,.2f}")
c2.metric("Sessions with credits", f"{len(with_credit):,}")
c3.metric("Avg credits / recorded session", f"{total / len(with_credit):,.2f}" if len(with_credit) else "—")
c4.metric("Credit coverage", f"{len(with_credit)}/{len(df)}")
st.info("Local session metadata may be incomplete. These are recorded credits, not a verified billing total. Projects are grouped by cwd directory name; worktrees may appear separately.")

left, right = st.columns(2)
with left:
    st.subheader("Daily credits")
    daily = with_credit.dropna(subset=["date"]).groupby("date", as_index=True)["credits"].sum()
    st.bar_chart(daily) if not daily.empty else st.caption("No dated credit records.")
with right:
    st.subheader("Credits by project")
    by_project = with_credit.groupby("project")["credits"].sum().sort_values(ascending=False)
    st.bar_chart(by_project) if not by_project.empty else st.caption("No credit records.")

st.subheader("High-cost sessions")
sort_df = with_credit.sort_values("credits", ascending=False)
top_n = st.slider("Show top sessions", 5, 100, 20, 5)
display_cols = ["credits", "title", "created_at", "updated_at", "project", "turns", "session_id"]
st.dataframe(sort_df[display_cols].head(top_n), use_container_width=True, hide_index=True)

st.subheader("Session details")
if len(sort_df):
    session_ids = sort_df["session_id"].tolist()
    selected_id = st.selectbox("Select session", session_ids, format_func=lambda sid: (
        f"{float(sort_df.loc[sort_df.session_id == sid, 'credits'].iloc[0]):.2f} · "
        f"{sort_df.loc[sort_df.session_id == sid, 'title'].iloc[0][:85]}"
    ))
    item = sort_df.loc[sort_df.session_id == selected_id].iloc[0]
    st.json({k: (str(item[k]) if k in ("created_at", "updated_at") else item[k]) for k in display_cols + ["cwd", "parent_session_id"]})

st.download_button(
    "Download filtered sessions CSV",
    data=df.drop(columns=["date"]).to_csv(index=False).encode("utf-8-sig"),
    file_name="kirometer_sessions.csv",
    mime="text/csv",
)
