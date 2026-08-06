from __future__ import annotations

from typing import Any

import pandas as pd

from core.config import Settings
from core.utils import write_json


def run_data_quality_checks(df: pd.DataFrame, settings: Settings, report_name: str) -> dict[str, Any]:
    """Run data quality checks on the cleaned dataframe."""
    checks: list[dict[str, Any]] = []
    row_count = len(df)

    checks.append({"check": "row_count", "dimension": "completeness", "passed": row_count >= 1, "expected": ">= 1", "actual": row_count})

    paper_id_nulls = int(df["paper_id"].isna().sum()) if "paper_id" in df.columns else row_count
    checks.append({"check": "paper_id_not_null", "dimension": "completeness", "passed": paper_id_nulls == 0, "expected": "0 nulls", "actual": f"{paper_id_nulls} nulls"})

    paper_id_dupes = int(df["paper_id"].duplicated().sum()) if "paper_id" in df.columns else 0
    checks.append({"check": "paper_id_unique", "dimension": "uniqueness", "passed": paper_id_dupes == 0, "expected": "0 duplicates", "actual": f"{paper_id_dupes} duplicates"})

    title_nulls = int(df["title"].isna().sum()) if "title" in df.columns else row_count
    title_empty = int((df["title"].str.strip() == "").sum()) if "title" in df.columns else 0
    title_issues = title_nulls + title_empty
    checks.append({"check": "title_not_null", "dimension": "completeness", "passed": title_issues == 0, "expected": "0 null/empty", "actual": f"{title_issues} null/empty"})

    empty_summary = int((df["summary"].fillna("").str.strip().str.len() == 0).sum()) if "summary" in df.columns else row_count
    checks.append({"check": "summary_not_empty", "dimension": "completeness", "passed": empty_summary == 0, "expected": "0 empty summaries", "actual": f"{empty_summary} empty"})

    if "age_days" in df.columns:
        stale_rows = int((df["age_days"] > settings.freshness_threshold_days).sum())
        stale_pct = round(stale_rows / max(row_count, 1) * 100, 1)
    else:
        stale_rows = 0
        stale_pct = 0.0
    checks.append({"check": "freshness", "dimension": "timeliness", "passed": stale_rows == 0, "expected": f"0 rows older than {settings.freshness_threshold_days} days", "actual": f"{stale_rows} stale rows ({stale_pct}%)"})

    all_passed = all(c["passed"] for c in checks)
    result = {
        "report_name": report_name,
        "total_checks": len(checks),
        "passed": sum(1 for c in checks if c["passed"]),
        "failed": sum(1 for c in checks if not c["passed"]),
        "all_passed": all_passed,
        "checks": checks,
    }

    report_path = settings.paths.quality_dir / f"{report_name}.json"
    write_json(report_path, result)
    print(f"  Quality checks: {result['passed']}/{result['total_checks']} passed -> {report_path}")
    return result


def build_freshness_report(df: pd.DataFrame, settings: Settings, report_path) -> dict[str, Any]:
    """Build a freshness report."""
    total_rows = len(df)

    if df.empty or "published" not in df.columns:
        payload: dict[str, Any] = {
            "latest_published": None, "oldest_published": None, "stale_rows": 0,
            "total_rows": total_rows, "freshness_threshold_days": settings.freshness_threshold_days,
            "is_fresh": False, "reason": "No data available",
        }
        write_json(report_path, payload)
        return payload

    published_sorted = df["published"].dropna().sort_values()
    latest_published = str(published_sorted.iloc[-1]) if len(published_sorted) > 0 else None
    oldest_published = str(published_sorted.iloc[0]) if len(published_sorted) > 0 else None

    stale_rows = int((df["age_days"] > settings.freshness_threshold_days).sum()) if "age_days" in df.columns else 0
    is_fresh = stale_rows == 0

    payload = {
        "latest_published": latest_published, "oldest_published": oldest_published,
        "stale_rows": stale_rows, "total_rows": total_rows,
        "freshness_threshold_days": settings.freshness_threshold_days,
        "is_fresh": is_fresh,
        "reason": "All records within freshness threshold" if is_fresh else f"{stale_rows}/{total_rows} records exceed {settings.freshness_threshold_days}-day threshold",
    }

    write_json(report_path, payload)
    print(f"  Freshness report: {'FRESH' if is_fresh else 'STALE'} ({stale_rows} stale rows) -> {report_path}")
    return payload
