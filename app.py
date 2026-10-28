"""Kiro CLI 使用量ダッシュボード（ローカル履歴・読み取り専用）。"""
from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
import streamlit as st

from kirometer import DEFAULT_ROOT, load_sessions
from phase2 import project_name
from data_quality import audit_metadata
from turn_analysis import session_turns, prompt_previews

JST = ZoneInfo("Asia/Tokyo")
st.set_page_config(page_title="kirometer｜使用量分析", page_icon="📊", layout="wide")
st.title("📊 Kiro CLI 使用量分析")
st.caption("ローカル履歴から、いつ・どの作業でクレジットを使ったか確認できます。")

with st.expander("はじめての方へ：この画面の見方", expanded=True):
    st.markdown("""
**まずはこの順番で見るのがおすすめです。**

1. **消費クレジット**：選択した期間・プロジェクトで記録されている使用量。
2. **日別推移**：消費量が急に増えた日を探す。
3. **プロジェクト別**：どの作業場所で多く使っているか確認する。
4. **高コストセッション**：タイトルから、消費が多かった作業を特定する。

**セッション**はKiro CLIで行った一連の作業、**ターン**はユーザーの指示単位です。
クレジットは費用（金額）そのものではありません。
""")

@st.cache_data(ttl=60, show_spinner=False)
def get_data(directory: str):
    return load_sessions(Path(directory))

st.sidebar.header("絞り込み")
root = Path(st.sidebar.text_input("履歴フォルダ", value=str(DEFAULT_ROOT))).expanduser()
if not root.is_dir():
    st.error(f"履歴フォルダが見つかりません：{root}")
    st.stop()
if st.sidebar.button("🔄 履歴を再読み込み"):
    get_data.clear()
    st.rerun()

sessions, diagnostics = get_data(str(root))
normalize = st.sidebar.checkbox('Git Worktreeを統合する', value=True)
st.sidebar.caption(f"読み込み：{diagnostics['loaded']:,} / {diagnostics['files']:,} 件（不正：{diagnostics['invalid']:,} 件）")

rows = [{
    "session_id": s.session_id,
    "title": s.title,
    "project": project_name(s.cwd, normalize),
    "cwd": s.cwd,
    "created_at": s.created_at,
    "updated_at": s.updated_at,
    "credits": s.credits,
    "turns": s.turns,
    "parent_session_id": s.parent_session_id,
} for s in sessions]
if not rows:
    st.warning("セッション履歴がありません。")
    st.stop()

df = pd.DataFrame(rows)
for column in ("created_at", "updated_at"):
    df[column] = pd.to_datetime(df[column], utc=True, errors="coerce").dt.tz_convert(JST)
df["date"] = df["created_at"].dt.date

period = st.sidebar.selectbox("集計期間（作成日時・日本時間）", ["全期間", "過去7日", "過去30日"], index=0)
if period != "全期間":
    days = 7 if period == "過去7日" else 30
    cutoff = datetime.now(JST).date() - timedelta(days=days - 1)
    df = df[df["date"] >= cutoff]
projects = sorted(df["project"].unique().tolist())
selected = st.sidebar.multiselect("プロジェクト（フォルダ名）", projects, default=projects)
df = df[df["project"].isin(selected)]
search = st.sidebar.text_input("セッションタイトルで検索", placeholder="例：認証、テスト")
if search:
    df = df[df["title"].str.contains(search, case=False, regex=False, na=False)]

recorded = df[df["credits"].notna()].copy()
total = float(recorded["credits"].sum())
count = len(recorded)
st.subheader("① 使用状況の概要")
c1, c2, c3, c4 = st.columns(4)
c1.metric("消費クレジット", f"{total:,.2f}", help="ローカル履歴に記録された値の合計。請求額とは異なります。")
c2.metric("集計できたセッション", f"{count:,} 件", help="クレジット記録のあるセッション数です。")
c3.metric("1セッション平均", f"{total / count:,.2f}" if count else "—", help="消費クレジット ÷ クレジット記録のあるセッション数。")
c4.metric("取得率", f"{count:,} / {len(df):,} 件", help="対象セッションのうち、クレジット記録がある件数。記録なしは0クレジットとは限りません。")
st.caption("※ 数値はローカル履歴ベースです。請求値との一致は未検証で、親子セッション間で重複する可能性もあります。")

left, right = st.columns(2)
with left:
    st.subheader("② 日別の消費量")
    st.caption("棒が高い日ほど多くのクレジットを消費。日付はセッション作成日（日本時間）を使用。")
    daily = recorded.dropna(subset=["date"]).groupby("date")["credits"].sum().sort_index()
    if daily.empty:
        st.info("対象期間に日時付きの使用量記録がありません。")
    else:
        st.bar_chart(daily, x_label="日付", y_label="クレジット")
with right:
    st.subheader("③ プロジェクト別の消費量")
    st.caption("作業フォルダ単位の比較です。mainなどのGit Worktreeは別集計になる場合があります。")
    by_project = recorded.groupby("project")["credits"].sum().sort_values(ascending=False)
    if by_project.empty:
        st.info("対象期間に使用量記録がありません。")
    else:
        st.bar_chart(by_project, x_label="プロジェクト", y_label="クレジット")

st.subheader("④ クレジット消費が多いセッション")
st.caption("上から順に消費量が多い作業です。タイトルや日時を見て、どの作業で増えたか調べられます。")
ranking = recorded.sort_values("credits", ascending=False)
top_n = st.slider("表示件数", 5, 100, 20, 5)
table = ranking[["credits", "title", "created_at", "updated_at", "project", "turns", "session_id"]].head(top_n).copy()
st.dataframe(
    table,
    use_container_width=True,
    hide_index=True,
    column_config={
        "credits": st.column_config.NumberColumn("クレジット", format="%.2f", help="当該セッションで記録された使用量"),
        "title": "セッションタイトル",
        "created_at": st.column_config.DatetimeColumn("開始日時", format="YYYY-MM-DD HH:mm"),
        "updated_at": st.column_config.DatetimeColumn("最終更新", format="YYYY-MM-DD HH:mm"),
        "project": "プロジェクト",
        "turns": "ターン数",
        "session_id": "セッションID",
    },
)

st.subheader("⑤ セッション詳細")
st.caption("ランキングから気になるセッションを選んで、日時や作業ディレクトリを確認します。")
if len(ranking):
    selected_id = st.selectbox(
        "対象セッション",
        ranking["session_id"].tolist(),
        format_func=lambda sid: (
            f"{ranking.loc[ranking.session_id == sid, 'credits'].iloc[0]:.2f} credits ｜ "
            f"{str(ranking.loc[ranking.session_id == sid, 'title'].iloc[0])[:80]}"
        ),
    )
    item = ranking.loc[ranking.session_id == selected_id].iloc[0]
    st.write(f"**タイトル：** {item['title']}")
    st.write(f"**消費量：** {item['credits']:.2f} credits　　**ターン数：** {item['turns']}")
    st.write(f"**プロジェクト：** {item['project']}")
    st.write(f"**開始：** {item['created_at']}　　**最終更新：** {item['updated_at']}")
    with st.expander("技術情報（パス・セッションID）"):
        st.code(f"cwd: {item['cwd']}\nsession_id: {item['session_id']}\nparent_session_id: {item['parent_session_id']}")
else:
    st.info("選択した条件にクレジット記録のあるセッションがありません。")

st.download_button(
    "📥 絞り込み結果をCSVで保存",
    data=df.drop(columns=["date"]).to_csv(index=False).encode("utf-8-sig"),
    file_name="kirometer_sessions.csv",
    mime="text/csv",
    help="タイトルと作業パスが含まれます。公開リポジトリへのアップロードには注意してください。",
)


st.subheader("⑥ ターン別のクレジット消費")
st.caption("上の「⑤ セッション詳細」で選んだセッションを、指示（ターン）ごとに分解します。指示内容は明示的に許可した場合のみローカルで表示します。")
if len(ranking):
    show_prompts = st.checkbox("指示内容を表示（機密情報に注意）", value=False)
    turn_rows = session_turns(root, selected_id)
    if turn_rows:
        turns_df = pd.DataFrame(turn_rows)
        if show_prompts:
            prompts = prompt_previews(root / (selected_id + ".jsonl"))
            if len(prompts) == len(turns_df):
                turns_df["指示内容（冒頭）"] = prompts
                st.caption("Promptイベントと課金ターンを出現順で対応付けた暫定表示です。")
            else:
                st.warning(f"Prompt {len(prompts)}件、課金ターン {len(turns_df)}件で件数が一致しないため指示内容は表示しません。")
        valid_turns = turns_df.dropna(subset=["credits"])
        st.metric("記録があるターン", f"{len(valid_turns)} / {len(turns_df)}")
        if not valid_turns.empty:
            st.bar_chart(valid_turns.set_index("turn")["credits"], x_label="ターン番号", y_label="クレジット")
            st.dataframe(
                valid_turns.sort_values("credits", ascending=False).rename(columns={"turn": "ターン番号", "credits": "クレジット"}),
                use_container_width=True, hide_index=True
            )
            session_total = float(item["credits"])
            turn_total = float(valid_turns["credits"].sum())
            if abs(session_total - turn_total) > 0.001:
                st.warning(f"セッション合計とターン合計に差があります（{session_total:.2f} / {turn_total:.2f}）。")
    else:
        st.info("このセッションにターンごとの使用量は見つかりませんでした。")


st.divider()
with st.expander("📋 データ取得品質とモデル情報の調査", expanded=False):
    st.caption("Kiro CLI 2.35.1のJSONメタデータだけを検査します。会話・モデル名・ファイルパスなどの値は表示しません。")
    @st.cache_data(ttl=60)
    def audit(directory: str):
        return audit_metadata(Path(directory))
    if st.button("取得状況を検査"):
        report = audit(str(root))
        n = report["counts"]
        a, b, d = st.columns(3)
        a.metric("読み取り可能なJSON", f"{n.get('files', 0) - n.get('unreadable', 0):,}件")
        b.metric("クレジット記録のあるターン", f"{n.get('metered_turns', 0):,} / {n.get('turns', 0):,}")
        d.metric("クレジット記録のないセッション", f"{n.get('unmetered_sessions', 0):,}件")
        if report["model_fields"]:
            st.write("**モデル関連フィールドが見つかった場所と出現件数**")
            st.dataframe(pd.DataFrame(
                [{"フィールド": k, "出現数": v} for k, v in report["model_fields"].items()]
            ), hide_index=True, use_container_width=True)
            st.info("モデルのフィールドが存在しても、モデル別クレジットを計算できるとは限りません。課金記録との対応付けは別途検証が必要です。")
        else:
            st.info("今回調べたメタデータ階層にはモデル識別フィールドが見つかりませんでした。現時点ではモデル別使用量を算出しません。")
        st.caption("SQLiteやJSONLのモデル情報については未調査です。これらを解析しても、モデル別クレジットが正確に求められるとは限りません。")
