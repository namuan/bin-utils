#!/usr/bin/env -S uv run --quiet --script
# /// script
# dependencies = [
#   "pandas",
#   "plotly",
# ]
# ///
"""
Analyze browser history.

Features:
- Estimated time spent per domain
- Visit frequency over time (daily)

Usage:
./vivaldi_history_analysis.py -h
./vivaldi_history_analysis.py -v
./vivaldi_history_analysis.py -vv
"""
import ipaddress
import logging
import math
import shutil
import sqlite3
import subprocess
import tempfile
from argparse import ArgumentParser, RawDescriptionHelpFormatter
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import urlparse

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio

VIVALDI_HISTORY_PATH = Path.home() / "Library/Application Support/Vivaldi/Default/History"

MAX_GAP_SECONDS = 30 * 60  # cap dwell time at 30 minutes


def setup_logging(verbosity):
    logging_level = logging.WARNING
    if verbosity == 1:
        logging_level = logging.INFO
    elif verbosity >= 2:
        logging_level = logging.DEBUG

    logging.basicConfig(
        handlers=[logging.StreamHandler()],
        format="%(asctime)s - %(filename)s:%(lineno)d - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        level=logging_level,
    )
    logging.captureWarnings(capture=True)


def parse_args():
    parser = ArgumentParser(
        description=__doc__,
        formatter_class=RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        dest="verbose",
        help="Increase verbosity of logging output",
    )
    parser.add_argument(
        "--open",
        action="store_true",
        help="Open the generated HTML dashboard with the system browser",
    )
    return parser.parse_args()


def chrome_time_to_datetime(chrome_time: int) -> datetime:
    """Convert Chromium timestamp to datetime."""
    return datetime(1601, 1, 1) + timedelta(microseconds=chrome_time)


def _extract_domain(url: str | None) -> str | None:
    if not url:
        return None
    parsed = urlparse(url)
    return parsed.hostname


def _is_local_domain(domain: str | None) -> bool:
    if not domain:
        return True

    d = domain.strip().strip("[]").lower()
    if not d:
        return True

    if d == "localhost":
        return True

    if d.endswith(".local"):
        return True

    try:
        ip = ipaddress.ip_address(d)
    except ValueError:
        return False

    return bool(ip.is_loopback or ip.is_private or ip.is_link_local)


def load_history_df() -> pd.DataFrame:
    logging.info("Loading browser history database")

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_db = Path(tmpdir) / "History"
        shutil.copy2(VIVALDI_HISTORY_PATH, tmp_db)
        logging.debug(f"Copied History DB to {tmp_db}")

        conn = sqlite3.connect(tmp_db)
        query = """
            SELECT
                urls.url,
                visits.visit_time
            FROM visits
            JOIN urls ON visits.url = urls.id
            ORDER BY visits.visit_time
        """
        df = pd.read_sql_query(query, conn)
        conn.close()

    logging.info(f"Loaded {len(df)} history rows")

    df["visited_at"] = df["visit_time"].apply(chrome_time_to_datetime)
    df["domain"] = df["url"].apply(_extract_domain)

    df = df.dropna(subset=["domain"]).reset_index(drop=True)
    df = df[~df["domain"].apply(_is_local_domain)].reset_index(drop=True)
    return df


def ensure_enriched_history_df(df: pd.DataFrame) -> pd.DataFrame:
    df = df.sort_values("visited_at").reset_index(drop=True)

    if "prev_visit" not in df.columns:
        df["prev_visit"] = df["visited_at"].shift(1)
    if "next_visit" not in df.columns:
        df["next_visit"] = df["visited_at"].shift(-1)

    if "gap_from_prev_seconds" not in df.columns:
        df["gap_from_prev_seconds"] = (df["visited_at"] - df["prev_visit"]).dt.total_seconds()

    if "raw_gap_to_next_seconds" not in df.columns:
        df["raw_gap_to_next_seconds"] = (df["next_visit"] - df["visited_at"]).dt.total_seconds()

    if "delta_seconds" not in df.columns:
        df["delta_seconds"] = df["raw_gap_to_next_seconds"].clip(lower=0, upper=MAX_GAP_SECONDS)

    if "date" not in df.columns:
        df["date"] = df["visited_at"].dt.date
    if "hour" not in df.columns:
        df["hour"] = df["visited_at"].dt.hour
    if "weekday" not in df.columns:
        df["weekday"] = df["visited_at"].dt.weekday
    if "is_weekend" not in df.columns:
        df["is_weekend"] = df["weekday"] >= 5

    return df


def categorize_domain(domain: str) -> str:
    d = (domain or "").lower()
    if not d:
        return "Unknown"

    rules: list[tuple[str, tuple[str, ...]]] = [
        ("Video", ("youtube.", "youtu.be", "vimeo.", "netflix.", "twitch.", "primevideo.", "hbomax.")),
        ("Social", ("twitter.", "x.com", "reddit.", "facebook.", "instagram.", "tiktok.", "linkedin.")),
        ("Search", ("google.", "duckduckgo.", "bing.", "kagi.", "brave.com/search")),
        ("News", ("news.", "nytimes.", "wsj.", "bbc.", "theguardian.", "cnn.", "ycombinator.", "medium.")),
        ("Shopping", ("amazon.", "ebay.", "etsy.", "walmart.", "bestbuy.", "target.")),
        ("Dev", ("github.", "gitlab.", "bitbucket.", "stackoverflow.", "docs.", "pypi.", "npmjs.", "packages.")),
        ("AI", ("openai.", "chatgpt.", "claude.", "anthropic.", "perplexity.", "huggingface.")),
        ("Email", ("mail.google.", "outlook.", "proton.me", "fastmail.", "icloud.com/mail")),
        ("Docs", ("notion.", "confluence.", "drive.google.", "docs.google.", "slack.", "teams.", "figma.")),
    ]
    for category, needles in rules:
        if any(n in d for n in needles):
            return category
    return "Other"


def analyze_time_per_domain(df: pd.DataFrame) -> pd.DataFrame:
    logging.info("Analyzing time spent per domain")

    df = ensure_enriched_history_df(df)

    result = df.groupby("domain")["delta_seconds"].sum().sort_values(ascending=False).reset_index()

    result["hours"] = result["delta_seconds"] / 3600
    return result


def analyze_frequency_over_time(df: pd.DataFrame) -> pd.DataFrame:
    logging.info("Analyzing visit frequency over time")

    df = ensure_enriched_history_df(df)
    return df.groupby("date").size().reset_index(name="visit_count").sort_values("date")


def build_dashboard_html(
    *,
    df: pd.DataFrame,
    time_per_domain: pd.DataFrame,
    frequency_over_time: pd.DataFrame,
) -> str:
    pio.templates.default = "plotly_dark"

    df = ensure_enriched_history_df(df)

    def fig_to_html(fig: go.Figure, *, include_js: bool) -> str:
        return pio.to_html(fig, include_plotlyjs="cdn" if include_js else False, full_html=False)

    top_n = 50
    top = time_per_domain[["domain", "hours"]].head(top_n).copy()
    if top.empty:
        fig_time = px.bar(title="Top domains (estimated time spent)")
    else:
        top = top.sort_values("hours", ascending=True)
        fig_time = px.bar(
            top,
            x="hours",
            y="domain",
            orientation="h",
            title="Top domains (estimated time spent)",
            labels={"hours": "Hours", "domain": "Domain"},
        )
        fig_time.update_layout(height=700, margin=dict(l=160, r=20, t=60, b=40))

    freq = frequency_over_time[["date", "visit_count"]].copy()
    if freq.empty:
        fig_freq = px.line(title="Visits over time (daily)")
    else:
        fig_freq = px.line(
            freq,
            x="date",
            y="visit_count",
            title="Visits over time (daily)",
            labels={"visit_count": "Visits", "date": "Date"},
        )
        fig_freq.update_traces(mode="lines+markers")
        fig_freq.update_layout(height=420, margin=dict(l=50, r=20, t=60, b=40))
        fig_freq.update_xaxes(rangeslider_visible=True)

    daily_time = df.groupby("date")["delta_seconds"].sum().reset_index()
    daily_time["hours"] = daily_time["delta_seconds"] / 3600
    daily = freq.merge(daily_time[["date", "hours"]], on="date", how="outer").fillna(0).sort_values("date")
    daily["rolling_visits_7d"] = daily["visit_count"].rolling(7, min_periods=1).mean()
    daily["rolling_hours_7d"] = daily["hours"].rolling(7, min_periods=1).mean()

    fig_rolling = go.Figure()
    fig_rolling.add_trace(
        go.Scatter(x=daily["date"], y=daily["rolling_visits_7d"], name="Visits (7d avg)", mode="lines")
    )
    fig_rolling.add_trace(
        go.Scatter(x=daily["date"], y=daily["rolling_hours_7d"], name="Hours (7d avg)", mode="lines", yaxis="y2")
    )
    fig_rolling.update_layout(
        title="Rolling activity (7-day average)",
        height=420,
        margin=dict(l=50, r=50, t=60, b=40),
        yaxis=dict(title="Visits"),
        yaxis2=dict(title="Hours", overlaying="y", side="right"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
    )

    dow_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    heat_df = df.copy()
    heat_df["dow"] = pd.Categorical(
        heat_df["weekday"].map(lambda i: dow_names[int(i)]), categories=dow_names, ordered=True
    )
    heat = heat_df.groupby(["dow", "hour"], observed=False).size().reset_index(name="visits")
    heat_pivot = heat.pivot(index="dow", columns="hour", values="visits").fillna(0).astype(int)
    fig_heatmap = px.imshow(
        heat_pivot,
        aspect="auto",
        title="Visits heatmap (day of week × hour)",
        labels=dict(x="Hour", y="Day", color="Visits"),
        color_continuous_scale="Blues",
    )
    fig_heatmap.update_layout(height=420, margin=dict(l=60, r=20, t=60, b=40))

    weekly = (
        df.set_index("visited_at")
        .groupby([pd.Grouper(freq="W-MON"), "domain"])["delta_seconds"]
        .sum()
        .reset_index()
        .rename(columns={"visited_at": "week"})
    )
    weekly["hours"] = weekly["delta_seconds"] / 3600
    top_domains_for_trends = time_per_domain["domain"].head(10).tolist()
    weekly_top = weekly[weekly["domain"].isin(top_domains_for_trends)].copy()
    fig_trends = px.area(
        weekly_top,
        x="week",
        y="hours",
        color="domain",
        title="Top domain time trends (weekly)",
        labels={"week": "Week", "hours": "Hours", "domain": "Domain"},
    )
    fig_trends.update_layout(height=520, margin=dict(l=50, r=20, t=60, b=40))

    distinct_daily_domains = df[["date", "domain"]].drop_duplicates()
    first_seen = df.groupby("domain")["date"].min()
    distinct_daily_domains["first_seen_date"] = distinct_daily_domains["domain"].map(first_seen)
    distinct_daily_domains["is_new"] = distinct_daily_domains["date"] == distinct_daily_domains["first_seen_date"]
    new_vs_returning = (
        distinct_daily_domains.groupby(["date", "is_new"])
        .size()
        .reset_index(name="domain_count")
        .replace({True: "New", False: "Returning"})
    )
    new_vs_returning = new_vs_returning.rename(columns={"is_new": "type"})
    fig_new_returning = px.bar(
        new_vs_returning,
        x="date",
        y="domain_count",
        color="type",
        title="New vs returning domains (daily distinct domains)",
        labels={"domain_count": "Distinct domains", "date": "Date", "type": "Type"},
        barmode="stack",
    )
    fig_new_returning.update_layout(height=420, margin=dict(l=50, r=20, t=60, b=40))
    fig_new_returning.update_xaxes(rangeslider_visible=True)

    def _entropy(ps: list[float]) -> float:
        return float(-sum(p * math.log(p) for p in ps if p > 0))

    def _hhi(ps: list[float]) -> float:
        return float(sum(p * p for p in ps if p > 0))

    per_week_domain = weekly.copy()
    per_week_domain["total"] = per_week_domain.groupby("week")["delta_seconds"].transform("sum").replace({0: 1})
    per_week_domain["p"] = per_week_domain["delta_seconds"] / per_week_domain["total"]
    diversity = per_week_domain.groupby("week")["p"].apply(list).reset_index(name="ps")
    diversity["entropy"] = diversity["ps"].apply(_entropy)
    diversity["hhi"] = diversity["ps"].apply(_hhi)
    diversity["effective_domains"] = diversity["entropy"].apply(lambda e: math.exp(e))
    fig_diversity = go.Figure()
    fig_diversity.add_trace(
        go.Scatter(
            x=diversity["week"], y=diversity["effective_domains"], name="Effective domains", mode="lines+markers"
        )
    )
    fig_diversity.add_trace(
        go.Scatter(
            x=diversity["week"], y=diversity["hhi"], name="HHI (concentration)", mode="lines+markers", yaxis="y2"
        )
    )
    fig_diversity.update_layout(
        title="Diversity vs concentration (weekly)",
        height=420,
        margin=dict(l=50, r=50, t=60, b=40),
        yaxis=dict(title="Effective # domains"),
        yaxis2=dict(title="HHI", overlaying="y", side="right"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
    )

    session_break = (
        df["gap_from_prev_seconds"].isna()
        | (df["gap_from_prev_seconds"] > MAX_GAP_SECONDS)
        | (df["gap_from_prev_seconds"] < 0)
    )
    session_id = session_break.cumsum()
    sessions = (
        df.assign(session_id=session_id)
        .groupby("session_id")
        .agg(
            session_start=("visited_at", "min"),
            session_end=("visited_at", "max"),
            visit_count=("visited_at", "size"),
            distinct_domains=("domain", "nunique"),
            estimated_seconds=("delta_seconds", "sum"),
        )
        .reset_index(drop=True)
    )
    sessions["duration_minutes"] = (sessions["session_end"] - sessions["session_start"]).dt.total_seconds() / 60
    sessions["estimated_minutes"] = sessions["estimated_seconds"] / 60

    fig_sessions_hist = px.histogram(
        sessions,
        x="duration_minutes",
        nbins=60,
        title="Session length distribution (minutes)",
        labels={"duration_minutes": "Session duration (min)"},
    )
    fig_sessions_hist.update_layout(height=420, margin=dict(l=50, r=20, t=60, b=40))

    fig_sessions_scatter = px.scatter(
        sessions,
        x="session_start",
        y="duration_minutes",
        size="visit_count",
        title="Sessions over time (size = visits in session)",
        labels={"session_start": "Session start", "duration_minutes": "Duration (min)", "visit_count": "Visits"},
    )
    fig_sessions_scatter.update_layout(height=420, margin=dict(l=50, r=20, t=60, b=40))

    gaps = df[["domain", "visited_at", "next_visit", "raw_gap_to_next_seconds", "delta_seconds"]].copy()
    gaps = gaps.dropna(subset=["raw_gap_to_next_seconds", "next_visit"])
    gaps = gaps[gaps["raw_gap_to_next_seconds"] > 0].copy()
    gaps["raw_minutes"] = gaps["raw_gap_to_next_seconds"] / 60
    gaps["capped_minutes"] = gaps["delta_seconds"] / 60
    gaps_top = gaps.sort_values("raw_gap_to_next_seconds", ascending=False).head(30)
    fig_gaps_table = go.Figure(
        data=[
            go.Table(
                header=dict(values=["Domain", "Visited at", "Next visit", "Raw gap (min)", "Capped (min)"]),
                cells=dict(
                    values=[
                        gaps_top["domain"].tolist(),
                        gaps_top["visited_at"].dt.strftime("%Y-%m-%d %H:%M:%S").tolist(),
                        gaps_top["next_visit"].dt.strftime("%Y-%m-%d %H:%M:%S").tolist(),
                        [f"{v:.1f}" for v in gaps_top["raw_minutes"].tolist()],
                        [f"{v:.1f}" for v in gaps_top["capped_minutes"].tolist()],
                    ]
                ),
            )
        ]
    )
    fig_gaps_table.update_layout(
        title="Longest gaps between visits (top 30)", height=520, margin=dict(l=20, r=20, t=60, b=20)
    )

    cat_df = df.copy()
    cat_df["category"] = cat_df["domain"].map(categorize_domain)
    cat_time = cat_df.groupby("category")["delta_seconds"].sum().reset_index()
    cat_time["hours"] = cat_time["delta_seconds"] / 3600
    cat_time = cat_time.sort_values("hours", ascending=True)
    fig_categories = px.bar(
        cat_time,
        x="hours",
        y="category",
        orientation="h",
        title="Time by category",
        labels={"hours": "Hours", "category": "Category"},
    )
    fig_categories.update_layout(height=420, margin=dict(l=120, r=20, t=60, b=40))

    top_domains_drill = time_per_domain["domain"].head(20).tolist()
    drill_base = df[df["domain"].isin(top_domains_drill)].copy()
    drill_visits = drill_base.groupby(["date", "domain"]).size().reset_index(name="visits")
    drill_time = drill_base.groupby(["date", "domain"])["delta_seconds"].sum().reset_index()
    drill_time["hours"] = drill_time["delta_seconds"] / 3600
    all_dates = sorted(df["date"].unique())

    fig_drill_visits = go.Figure()
    for i, domain in enumerate(top_domains_drill):
        s = drill_visits[drill_visits["domain"] == domain].set_index("date").reindex(all_dates, fill_value=0)["visits"]
        fig_drill_visits.add_trace(
            go.Scatter(x=all_dates, y=s.tolist(), name=domain, visible=(i == 0), mode="lines+markers")
        )
    buttons = []
    for i, domain in enumerate(top_domains_drill):
        visible = [False] * len(top_domains_drill)
        visible[i] = True
        buttons.append(
            dict(
                label=domain,
                method="update",
                args=[{"visible": visible}, {"title": f"Daily visits (select domain): {domain}"}],
            )
        )
    fig_drill_visits.update_layout(
        title=f"Daily visits (select domain): {top_domains_drill[0] if top_domains_drill else ''}",
        height=420,
        margin=dict(l=50, r=20, t=60, b=40),
        updatemenus=[
            dict(
                buttons=buttons,
                direction="down",
                x=0,
                y=1.15,
                xanchor="left",
                yanchor="top",
                bgcolor="rgba(230, 237, 247, 0.95)",
                bordercolor="rgba(0, 0, 0, 0.35)",
                font=dict(color="#0b1220", size=12),
            )
        ],
    )

    fig_drill_hours = go.Figure()
    for i, domain in enumerate(top_domains_drill):
        s = drill_time[drill_time["domain"] == domain].set_index("date").reindex(all_dates, fill_value=0)["hours"]
        fig_drill_hours.add_trace(
            go.Scatter(x=all_dates, y=s.tolist(), name=domain, visible=(i == 0), mode="lines+markers")
        )
    buttons2 = []
    for i, domain in enumerate(top_domains_drill):
        visible = [False] * len(top_domains_drill)
        visible[i] = True
        buttons2.append(
            dict(
                label=domain,
                method="update",
                args=[{"visible": visible}, {"title": f"Daily hours (select domain): {domain}"}],
            )
        )
    fig_drill_hours.update_layout(
        title=f"Daily hours (select domain): {top_domains_drill[0] if top_domains_drill else ''}",
        height=420,
        margin=dict(l=50, r=20, t=60, b=40),
        updatemenus=[
            dict(
                buttons=buttons2,
                direction="down",
                x=0,
                y=1.15,
                xanchor="left",
                yanchor="top",
                bgcolor="rgba(230, 237, 247, 0.95)",
                bordercolor="rgba(0, 0, 0, 0.35)",
                font=dict(color="#0b1220", size=12),
            )
        ],
    )

    by_hour = df.groupby(["is_weekend", "hour"]).size().reset_index(name="visits")
    by_hour["day_type"] = by_hour["is_weekend"].map({True: "Weekend", False: "Weekday"})
    fig_weekday_weekend_visits = px.line(
        by_hour,
        x="hour",
        y="visits",
        color="day_type",
        title="Visits by hour: weekday vs weekend",
        labels={"hour": "Hour", "visits": "Visits", "day_type": "Day type"},
    )
    fig_weekday_weekend_visits.update_traces(mode="lines+markers")
    fig_weekday_weekend_visits.update_layout(height=420, margin=dict(l=50, r=20, t=60, b=40))

    by_hour_time = df.groupby(["is_weekend", "hour"])["delta_seconds"].sum().reset_index()
    by_hour_time["hours"] = by_hour_time["delta_seconds"] / 3600
    by_hour_time["day_type"] = by_hour_time["is_weekend"].map({True: "Weekend", False: "Weekday"})
    fig_weekday_weekend_hours = px.line(
        by_hour_time,
        x="hour",
        y="hours",
        color="day_type",
        title="Estimated time by hour: weekday vs weekend",
        labels={"hour": "Hour", "hours": "Hours", "day_type": "Day type"},
    )
    fig_weekday_weekend_hours.update_traces(mode="lines+markers")
    fig_weekday_weekend_hours.update_layout(height=420, margin=dict(l=50, r=20, t=60, b=40))

    daily_for_outliers = daily.copy()
    daily_for_outliers["visits_z"] = 0.0
    daily_for_outliers["hours_z"] = 0.0
    if daily_for_outliers["visit_count"].std(ddof=0) > 0:
        daily_for_outliers["visits_z"] = (
            daily_for_outliers["visit_count"] - daily_for_outliers["visit_count"].mean()
        ) / daily_for_outliers["visit_count"].std(ddof=0)
    if daily_for_outliers["hours"].std(ddof=0) > 0:
        daily_for_outliers["hours_z"] = (
            daily_for_outliers["hours"] - daily_for_outliers["hours"].mean()
        ) / daily_for_outliers["hours"].std(ddof=0)
    daily_for_outliers["is_outlier"] = (daily_for_outliers["visits_z"].abs() > 2.5) | (
        daily_for_outliers["hours_z"].abs() > 2.5
    )
    fig_outliers = px.scatter(
        daily_for_outliers,
        x="date",
        y="hours",
        size="visit_count",
        color="is_outlier",
        title="Daily outliers (hours vs visits)",
        labels={"date": "Date", "hours": "Hours", "visit_count": "Visits", "is_outlier": "Outlier"},
    )
    fig_outliers.update_layout(height=420, margin=dict(l=50, r=20, t=60, b=40))

    work_start = 9
    work_end = 17
    work_df = df.copy()
    work_df["bucket"] = "After hours"
    work_mask = (work_df["weekday"] < 5) & (work_df["hour"] >= work_start) & (work_df["hour"] < work_end)
    work_df.loc[work_mask, "bucket"] = "Work hours"
    work_by_domain = work_df.groupby(["domain", "bucket"])["delta_seconds"].sum().reset_index()
    work_by_domain["hours"] = work_by_domain["delta_seconds"] / 3600
    totals = work_by_domain.groupby("domain")["hours"].sum().sort_values(ascending=False).head(20).index.tolist()
    work_by_domain = work_by_domain[work_by_domain["domain"].isin(totals)].copy()
    work_by_domain = work_by_domain.sort_values(["bucket", "hours"], ascending=[True, True])
    fig_work_after = px.bar(
        work_by_domain,
        x="hours",
        y="domain",
        color="bucket",
        barmode="group",
        orientation="h",
        title=f"Work hours vs after hours (Mon–Fri {work_start:02d}:00–{work_end:02d}:00)",
        labels={"hours": "Hours", "domain": "Domain", "bucket": "Bucket"},
    )
    fig_work_after.update_layout(height=650, margin=dict(l=160, r=20, t=60, b=40))

    chart_time = fig_to_html(fig_time, include_js=True)
    chart_freq = fig_to_html(fig_freq, include_js=False)
    chart_rolling = fig_to_html(fig_rolling, include_js=False)
    chart_heatmap = fig_to_html(fig_heatmap, include_js=False)
    chart_trends = fig_to_html(fig_trends, include_js=False)
    chart_new_returning = fig_to_html(fig_new_returning, include_js=False)
    chart_diversity = fig_to_html(fig_diversity, include_js=False)
    chart_sessions_hist = fig_to_html(fig_sessions_hist, include_js=False)
    chart_sessions_scatter = fig_to_html(fig_sessions_scatter, include_js=False)
    chart_gaps_table = fig_to_html(fig_gaps_table, include_js=False)
    chart_categories = fig_to_html(fig_categories, include_js=False)
    chart_drill_visits = fig_to_html(fig_drill_visits, include_js=False)
    chart_drill_hours = fig_to_html(fig_drill_hours, include_js=False)
    chart_weekday_weekend_visits = fig_to_html(fig_weekday_weekend_visits, include_js=False)
    chart_weekday_weekend_hours = fig_to_html(fig_weekday_weekend_hours, include_js=False)
    chart_outliers = fig_to_html(fig_outliers, include_js=False)
    chart_work_after = fig_to_html(fig_work_after, include_js=False)
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    sections: list[tuple[str, str, str]] = [
        ("top-domains", "Top domains (estimated time spent)", chart_time),
        ("visits-over-time", "Visits over time (daily)", chart_freq),
        ("rolling-activity", "Rolling activity", chart_rolling),
        ("heatmap", "Time-of-day heatmap", chart_heatmap),
        ("domain-trends", "Domain trends", chart_trends),
        ("new-vs-returning", "New vs returning domains", chart_new_returning),
        ("diversity", "Diversity / concentration", chart_diversity),
        ("sessions-dist", "Session length distribution", chart_sessions_hist),
        ("sessions-over-time", "Sessions over time", chart_sessions_scatter),
        ("longest-gaps", "Longest dwell gaps", chart_gaps_table),
        ("categories", "Category breakdown", chart_categories),
        ("drilldown-visits", "Top-domain drilldown: visits", chart_drill_visits),
        ("drilldown-hours", "Top-domain drilldown: hours", chart_drill_hours),
        ("weekday-weekend-visits", "Weekday vs weekend: visits", chart_weekday_weekend_visits),
        ("weekday-weekend-hours", "Weekday vs weekend: hours", chart_weekday_weekend_hours),
        ("outliers", "Outlier detection", chart_outliers),
        ("work-vs-after", "Work hours vs after hours", chart_work_after),
    ]

    return "\n".join(
        [
            "<!doctype html>",
            '<html lang="en">',
            "<head>",
            '  <meta charset="utf-8" />',
            '  <meta name="viewport" content="width=device-width, initial-scale=1" />',
            "  <title>Browser History Dashboard</title>",
            "  <style>",
            "    :root {",
            "      --bg: #0b1220;",
            "      --panel: #0f1a2e;",
            "      --text: #e6edf7;",
            "      --muted: #a9b7d0;",
            "      --border: rgba(255,255,255,0.08);",
            "    }",
            "    body { margin: 0; background: var(--bg); color: var(--text); font: 14px/1.4 -apple-system, BlinkMacSystemFont, Segoe UI, Roboto, Helvetica, Arial, sans-serif; }",
            "    .container { max-width: 1100px; margin: 0 auto; padding: 28px 18px 48px; }",
            "    h1 { margin: 0 0 6px; font-size: 20px; font-weight: 650; }",
            "    .sub { color: var(--muted); margin: 0 0 18px; }",
            "    .nav { display: flex; flex-wrap: wrap; gap: 10px; margin: 12px 0 18px; }",
            "    .nav a { color: var(--muted); text-decoration: none; border: 1px solid var(--border); padding: 6px 10px; border-radius: 999px; font-size: 12px; }",
            "    .nav a:hover { color: var(--text); border-color: rgba(255,255,255,0.16); }",
            "    .grid { display: grid; grid-template-columns: 1fr; gap: 14px; }",
            "    .card { background: var(--panel); border: 1px solid var(--border); border-radius: 12px; padding: 14px 14px 12px; }",
            "    .card h2 { margin: 0 0 10px; font-size: 14px; color: var(--muted); font-weight: 650; letter-spacing: 0.02em; }",
            "    .footer { margin-top: 12px; color: var(--muted); font-size: 12px; }",
            "  </style>",
            "</head>",
            "<body>",
            '  <div class="container">',
            "    <h1>Browser History Dashboard</h1>",
            f'    <p class="sub">Generated at {generated_at}</p>',
            '    <div class="nav">',
            *[f'      <a href="#{sec_id}">{title}</a>' for sec_id, title, _ in sections],
            "    </div>",
            '    <div class="grid">',
            *[
                "\n".join(
                    [
                        f'      <div class="card" id="{sec_id}">',
                        f"        <h2>{title}</h2>",
                        f"{content}",
                        "      </div>",
                    ]
                )
                for sec_id, title, content in sections
            ],
            "    </div>",
            '    <div class="footer">Estimated dwell time is capped at 30 minutes per visit gap.</div>',
            "  </div>",
            "</body>",
            "</html>",
        ]
    )


def write_temp_dashboard_html(html: str) -> Path:
    tmp = tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        suffix=".html",
        prefix="vivaldi-history-dashboard-",
        delete=False,
    )
    with tmp:
        tmp.write(html)
    return Path(tmp.name)


def main(args):
    logging.debug(f"Verbosity level: {args.verbose}")

    df = load_history_df()

    time_per_domain = analyze_time_per_domain(df)
    frequency_over_time = analyze_frequency_over_time(df)

    print("\nTop domains by estimated time spent:\n")
    print(time_per_domain[["domain", "hours"]].head(20).to_string(index=False, formatters={"hours": "{:.2f}".format}))

    print("\nVisit frequency per day:\n")
    print(frequency_over_time.to_string(index=False))

    html = build_dashboard_html(
        df=df,
        time_per_domain=time_per_domain,
        frequency_over_time=frequency_over_time,
    )
    html_path = write_temp_dashboard_html(html)
    print(f"\nDashboard HTML: {html_path}\n")

    if args.open:
        subprocess.run(["open", str(html_path)], check=False)


if __name__ == "__main__":
    args = parse_args()
    setup_logging(args.verbose)
    main(args)
