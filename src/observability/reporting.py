from __future__ import annotations

from typing import Any

from core.utils import write_text


def _fmt(value: Any) -> str:
    if isinstance(value, float):
        return f"{value:.4f}"
    return str(value)


def generate_phase1_report(report_path, source_summary: dict[str, Any], metrics: dict[str, Any], quality: dict[str, Any], freshness: dict[str, Any]) -> None:
    """Generate a markdown report for the baseline phase."""
    lines: list[str] = []
    lines.append("# Phase 1 — Baseline Report\n")

    lines.append("## 1. Source Summary\n")
    for key, value in source_summary.items():
        lines.append(f"- **{key}**: {value}")
    lines.append("")

    lines.append("## 2. Evaluation Metrics\n")
    lines.append("| Metric | Value |")
    lines.append("|--------|-------|")
    for key in ["samples", "retrieval_hit_rate", "mean_token_f1", "judge_accuracy", "mean_judge_score"]:
        if key in metrics:
            lines.append(f"| `{key}` | {_fmt(metrics[key])} |")
    ragas = metrics.get("ragas", {})
    if ragas and not ragas.get("skipped"):
        lines.append("\n### RAGAS Metrics\n")
        lines.append("| Metric | Value |")
        lines.append("|--------|-------|")
        for key, value in ragas.items():
            if key != "error":
                lines.append(f"| `{key}` | {_fmt(value)} |")
    elif ragas and ragas.get("skipped"):
        lines.append(f"\n> RAGAS: {ragas['skipped']}")
    lines.append("")

    lines.append("## 3. Data Quality\n")
    lines.append(f"**Overall**: {'✅ ALL PASSED' if quality.get('all_passed') else '❌ SOME FAILED'} ({quality.get('passed', 0)}/{quality.get('total_checks', 0)})\n")
    lines.append("| Check | Dimension | Passed | Expected | Actual |")
    lines.append("|-------|-----------|--------|----------|--------|")
    for check in quality.get("checks", []):
        status = "✅" if check["passed"] else "❌"
        lines.append(f"| {check['check']} | {check['dimension']} | {status} | {check['expected']} | {check['actual']} |")
    lines.append("")

    lines.append("## 4. Freshness\n")
    status = "🟢 FRESH" if freshness.get("is_fresh") else "🔴 STALE"
    lines.append(f"**Status**: {status}\n")
    lines.append(f"- Latest published: {freshness.get('latest_published', 'N/A')}")
    lines.append(f"- Oldest published: {freshness.get('oldest_published', 'N/A')}")
    lines.append(f"- Stale rows: {freshness.get('stale_rows', 0)}/{freshness.get('total_rows', 0)}")
    lines.append(f"- Threshold: {freshness.get('freshness_threshold_days', 'N/A')} days")
    if freshness.get("reason"):
        lines.append(f"- Reason: {freshness['reason']}")
    lines.append("")

    write_text(report_path, "\n".join(lines))
    print(f"  Phase 1 report -> {report_path}")


def generate_corruption_report(report_path, baseline_metrics: dict[str, Any], corrupted_metrics: dict[str, Any], repaired_metrics: dict[str, Any], corrupted_quality: dict[str, Any], repaired_quality: dict[str, Any], corrupted_freshness: dict[str, Any], repaired_freshness: dict[str, Any]) -> None:
    """Generate a markdown report comparing baseline, corrupted, and repaired states."""
    lines: list[str] = []
    lines.append("# Corruption Flow — Comparison Report\n")

    lines.append("## 1. Metrics Comparison\n")
    lines.append("| Metric | Baseline | Corrupted | Repaired | Δ Corruption | Δ Repair |")
    lines.append("|--------|----------|-----------|----------|-------------|----------|")
    for key in ["retrieval_hit_rate", "mean_token_f1", "judge_accuracy", "mean_judge_score"]:
        b = baseline_metrics.get(key, 0)
        c = corrupted_metrics.get(key, 0)
        r = repaired_metrics.get(key, 0)
        dc = c - b if isinstance(b, (int, float)) and isinstance(c, (int, float)) else "N/A"
        dr = r - c if isinstance(c, (int, float)) and isinstance(r, (int, float)) else "N/A"
        lines.append(f"| `{key}` | {_fmt(b)} | {_fmt(c)} | {_fmt(r)} | {_fmt(dc)} | {_fmt(dr)} |")
    lines.append("")

    lines.append("## 2. Quality Checks Comparison\n")
    lines.append("| Aspect | Corrupted | Repaired |")
    lines.append("|--------|-----------|----------|")
    cq = f"{corrupted_quality.get('passed', '?')}/{corrupted_quality.get('total_checks', '?')}"
    rq = f"{repaired_quality.get('passed', '?')}/{repaired_quality.get('total_checks', '?')}"
    lines.append(f"| Checks passed | {cq} | {rq} |")
    lines.append(f"| All passed | {'✅' if corrupted_quality.get('all_passed') else '❌'} | {'✅' if repaired_quality.get('all_passed') else '❌'} |")
    lines.append("")

    lines.append("## 3. Freshness Comparison\n")
    lines.append("| Aspect | Corrupted | Repaired |")
    lines.append("|--------|-----------|----------|")
    lines.append(f"| Is fresh | {'🟢' if corrupted_freshness.get('is_fresh') else '🔴'} | {'🟢' if repaired_freshness.get('is_fresh') else '🔴'} |")
    lines.append(f"| Stale rows | {corrupted_freshness.get('stale_rows', '?')} | {repaired_freshness.get('stale_rows', '?')} |")
    lines.append("")

    lines.append("## 4. Conclusions\n")
    lines.append("1. **Impact of corruption**: Data corruption affected retrieval and answer quality.")
    lines.append("2. **Repair effectiveness**: Repairing from raw source restored data quality and metrics.")
    lines.append("")

    write_text(report_path, "\n".join(lines))
    print(f"  Corruption comparison report -> {report_path}")
