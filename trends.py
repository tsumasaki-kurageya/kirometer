"""Daily credit trends and transparent anomaly flags."""
from __future__ import annotations
from datetime import timedelta
import pandas as pd


def daily_trends(sessions: pd.DataFrame, multiplier: float = 2.0, minimum: float = 20.0) -> pd.DataFrame:
    """Only non-null recorded credits; comparison uses preceding 7 calendar days."""
    cols = ["date", "credits", "sessions", "previous_7d_avg", "is_spike"]
    if sessions.empty:
        return pd.DataFrame(columns=cols)
    frame = sessions.dropna(subset=["date", "credits"]).copy()
    if frame.empty:
        return pd.DataFrame(columns=cols)
    frame["date"] = pd.to_datetime(frame["date"])
    daily = frame.groupby("date").agg(credits=("credits", "sum"), sessions=("credits", "size"))
    dates = pd.date_range(daily.index.min(), daily.index.max(), freq="D")
    daily = daily.reindex(dates, fill_value=0)
    baseline = daily["credits"].shift(1).rolling(window=7, min_periods=3).mean()
    daily["previous_7d_avg"] = baseline
    daily["is_spike"] = baseline.notna() & (daily["credits"] >= minimum) & (daily["credits"] >= baseline * multiplier)
    daily.index.name = "date"
    return daily.reset_index()[cols]
