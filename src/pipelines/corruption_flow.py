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


def _save_dataframe(df: pd.DataFrame, csv_path, json_path) -> None:
    write_csv(df, csv_path)
    write_json(json_path, df.to_dict(orient="records"))


def _build_and_evaluate(settings, df: pd.DataFrame, embeddings_path, metrics_path, answers_path):
    index = LocalEmbeddingIndex.build(df=df, settings=settings, embeddings_output_path=embeddings_path)
    return evaluate_pipeline(
        settings=settings,
        index=index,
        test_set_path=settings.paths.eval_testset,
        metrics_output_path=metrics_path,
        answers_output_path=answers_path,
    )


def main() -> None:
    print("=" * 60)
    print("PHASE 2 — Corruption Flow")
    print("=" * 60)

    settings = load_settings()
    paths = settings.paths

    print("\n[1/8] Loading baseline artifacts...")
    baseline_metrics = read_json(paths.baseline_metrics)
    clean_df = pd.DataFrame(read_json(paths.clean_json))
    print(f"  Baseline clean data: {len(clean_df)} rows")
    print(f"  Baseline retrieval_hit_rate = {baseline_metrics['retrieval_hit_rate']:.4f}")

    print("\n[2/8] Corrupting clean data...")
    corrupted_df = corrupt_clean_dataframe(clean_df, paths.corruption_log)

    print("\n[3/8] Saving corrupted artifacts...")
    _save_dataframe(corrupted_df, paths.corrupted_clean_csv, paths.corrupted_clean_json)
    print(f"  {len(corrupted_df)} rows -> {paths.corrupted_clean_csv}")

    print("\n[4/8] Building corrupted index & evaluating...")
    corrupted_eval = _build_and_evaluate(
        settings, corrupted_df, paths.corrupted_embeddings_json, paths.corrupted_metrics, paths.corrupted_answers
    )
    print(f"  Corrupted retrieval_hit_rate = {corrupted_eval.summary['retrieval_hit_rate']:.4f}")

    print("\n[5/8] Running quality checks on corrupted data...")
    corrupted_quality = run_data_quality_checks(corrupted_df, settings, report_name="corrupted_quality")
    corrupted_freshness = build_freshness_report(
        corrupted_df, settings, paths.quality_dir / "corrupted_freshness_report.json"
    )

    print("\n[6/8] Repairing data from raw source...")
    raw_records = load_raw_records(paths.raw_records_json)
    repaired_df = build_clean_dataframe(raw_records, now_utc())
    _save_dataframe(repaired_df, paths.repaired_clean_csv, paths.repaired_clean_json)
    print(f"  Repaired clean data: {len(repaired_df)} rows")

    print("\n[7/8] Building repaired index & evaluating...")
    repaired_eval = _build_and_evaluate(
        settings, repaired_df, paths.repaired_embeddings_json, paths.repaired_metrics, paths.repaired_answers
    )
    print(f"  Repaired retrieval_hit_rate = {repaired_eval.summary['retrieval_hit_rate']:.4f}")

    repaired_quality = run_data_quality_checks(repaired_df, settings, report_name="repaired_quality")
    repaired_freshness = build_freshness_report(
        repaired_df, settings, paths.quality_dir / "repaired_freshness_report.json"
    )

    print("\n[8/8] Generating comparison report...")
    generate_corruption_report(
        report_path=paths.comparison_report,
        baseline_metrics=baseline_metrics,
        corrupted_metrics=corrupted_eval.summary,
        repaired_metrics=repaired_eval.summary,
        corrupted_quality=corrupted_quality,
        repaired_quality=repaired_quality,
        corrupted_freshness=corrupted_freshness,
        repaired_freshness=repaired_freshness,
    )

    print("\n" + "=" * 60)
    print("PHASE 2 COMPLETE")
    print("=" * 60)
    print(f"\n{'Metric':<25} {'Baseline':>10} {'Corrupted':>10} {'Repaired':>10}")
    print("-" * 57)
    for key in ["retrieval_hit_rate", "mean_token_f1", "judge_accuracy", "mean_judge_score"]:
        b = baseline_metrics.get(key, 0)
        c = corrupted_eval.summary.get(key, 0)
        r = repaired_eval.summary.get(key, 0)
        print(f"{key:<25} {b:>10.4f} {c:>10.4f} {r:>10.4f}")


if __name__ == "__main__":
    main()
