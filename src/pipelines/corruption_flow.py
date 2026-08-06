from __future__ import annotations

import pandas as pd

from core.config import load_settings
from core.utils import now_utc, read_json, write_csv, write_json
from evaluation.metrics import evaluate_pipeline
from ingestion.cleaning import build_clean_dataframe
from ingestion.corruption import corrupt_clean_dataframe
from ingestion.crossref import load_raw_records
from observability.quality import build_freshness_report, run_data_quality_checks
from observability.reporting import generate_corruption_report
from retrieval.index import LocalEmbeddingIndex


def main() -> None:
    """Build the corruption -> evaluate -> repair -> compare flow."""
    print("=" * 60)
    print("PHASE 2 — Corruption Flow")
    print("=" * 60)

    settings = load_settings()
    run_date = now_utc()

    print("\n[1/8] Loading baseline artifacts...")
    baseline_metrics = read_json(settings.paths.baseline_metrics)
    print(f"  Baseline metrics loaded: retrieval_hit_rate={baseline_metrics['retrieval_hit_rate']:.4f}")
    baseline_df = pd.read_csv(settings.paths.clean_csv)
    print(f"  Baseline clean data: {len(baseline_df)} rows")

    print("\n[2/8] Corrupting clean data...")
    corrupted_df = corrupt_clean_dataframe(baseline_df, settings.paths.corruption_log)

    print("\n[3/8] Saving corrupted artifacts...")
    write_csv(corrupted_df, settings.paths.corrupted_clean_csv)
    write_json(settings.paths.corrupted_clean_json, corrupted_df.to_dict(orient="records"))

    print("\n[4/8] Building corrupted index & evaluating...")
    corrupted_index = LocalEmbeddingIndex.build(df=corrupted_df, settings=settings, embeddings_output_path=settings.paths.corrupted_embeddings_json)
    corrupted_bundle = evaluate_pipeline(settings=settings, index=corrupted_index, test_set_path=settings.paths.eval_testset, metrics_output_path=settings.paths.corrupted_metrics, answers_output_path=settings.paths.corrupted_answers)
    corrupted_metrics = corrupted_bundle.summary
    print(f"  Corrupted retrieval_hit_rate = {corrupted_metrics['retrieval_hit_rate']:.4f}")

    print("\n[5/8] Running quality checks on corrupted data...")
    corrupted_quality = run_data_quality_checks(corrupted_df, settings, report_name="corrupted_quality")
    corrupted_freshness = build_freshness_report(corrupted_df, settings, settings.paths.quality_dir / "corrupted_freshness_report.json")

    print("\n[6/8] Repairing data from raw source...")
    raw_records = load_raw_records(settings.paths.raw_records_json)
    repaired_df = build_clean_dataframe(raw_records, run_date)
    write_csv(repaired_df, settings.paths.repaired_clean_csv)
    write_json(settings.paths.repaired_clean_json, repaired_df.to_dict(orient="records"))
    print(f"  Repaired clean data: {len(repaired_df)} rows")

    print("\n[7/8] Building repaired index & evaluating...")
    repaired_index = LocalEmbeddingIndex.build(df=repaired_df, settings=settings, embeddings_output_path=settings.paths.repaired_embeddings_json)
    repaired_bundle = evaluate_pipeline(settings=settings, index=repaired_index, test_set_path=settings.paths.eval_testset, metrics_output_path=settings.paths.repaired_metrics, answers_output_path=settings.paths.repaired_answers)
    repaired_metrics = repaired_bundle.summary
    print(f"  Repaired retrieval_hit_rate = {repaired_metrics['retrieval_hit_rate']:.4f}")

    repaired_quality = run_data_quality_checks(repaired_df, settings, report_name="repaired_quality")
    repaired_freshness = build_freshness_report(repaired_df, settings, settings.paths.quality_dir / "repaired_freshness_report.json")

    print("\n[8/8] Generating comparison report...")
    generate_corruption_report(
        report_path=settings.paths.comparison_report,
        baseline_metrics=baseline_metrics, corrupted_metrics=corrupted_metrics, repaired_metrics=repaired_metrics,
        corrupted_quality=corrupted_quality, repaired_quality=repaired_quality,
        corrupted_freshness=corrupted_freshness, repaired_freshness=repaired_freshness,
    )

    print("\n" + "=" * 60)
    print("PHASE 2 COMPLETE")
    print("=" * 60)
    print(f"\n{'Metric':<25} {'Baseline':>10} {'Corrupted':>10} {'Repaired':>10}")
    print("-" * 57)
    for key in ["retrieval_hit_rate", "mean_token_f1", "judge_accuracy", "mean_judge_score"]:
        b, c, r = baseline_metrics.get(key, 0), corrupted_metrics.get(key, 0), repaired_metrics.get(key, 0)
        print(f"{key:<25} {b:>10.4f} {c:>10.4f} {r:>10.4f}")
