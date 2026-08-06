"""Run baseline from teammate's clean data (skip fetch/clean steps)."""
from __future__ import annotations

import pandas as pd

from core.config import load_settings
from core.utils import now_utc, read_json
from evaluation.metrics import evaluate_pipeline
from evaluation.testset import build_test_set
from observability.quality import build_freshness_report, run_data_quality_checks
from observability.reporting import generate_phase1_report
from retrieval.index import LocalEmbeddingIndex


def main() -> None:
    print("=" * 60)
    print("BASELINE — Using Teammate's Clean Data")
    print("=" * 60)

    settings = load_settings()

    # 1. Load teammate's clean data directly
    print("\n[1/6] Loading teammate's clean data...")
    df = pd.read_csv(settings.paths.clean_csv)
    print(f"  Loaded {len(df)} rows from {settings.paths.clean_csv}")
    print(f"  Columns: {list(df.columns)}")

    # 2. Build embedding index
    print("\n[2/6] Building embedding index...")
    index = LocalEmbeddingIndex.build(
        df=df, settings=settings,
        embeddings_output_path=settings.paths.embeddings_json,
    )
    print(f"  Index built: {len(df)} docs in '{index.collection_name}'")

    # 3. Build evaluation test set
    print("\n[3/6] Building evaluation test set...")
    test_set = build_test_set(df, settings.paths.eval_testset)
    print(f"  Test set: {len(test_set)} questions")

    # 4. Evaluate
    print("\n[4/6] Evaluating baseline...")
    bundle = evaluate_pipeline(
        settings=settings, index=index,
        test_set_path=settings.paths.eval_testset,
        metrics_output_path=settings.paths.baseline_metrics,
        answers_output_path=settings.paths.baseline_answers,
    )
    metrics = bundle.summary
    print(f"  retrieval_hit_rate = {metrics['retrieval_hit_rate']:.4f}")
    print(f"  mean_token_f1     = {metrics['mean_token_f1']:.4f}")
    print(f"  judge_accuracy    = {metrics['judge_accuracy']:.4f}")
    print(f"  mean_judge_score  = {metrics['mean_judge_score']:.4f}")

    # 5. Quality + freshness
    print("\n[5/6] Running quality checks...")
    quality = run_data_quality_checks(df, settings, report_name="baseline_quality")
    freshness = build_freshness_report(df, settings, settings.paths.freshness_report)

    # 6. Report
    print("\n[6/6] Generating phase 1 report...")
    source_summary = {
        "source": "teammate_clean_data",
        "records_after_cleaning": len(df),
        "embedding_model": settings.embedding_model,
        "llm_provider": settings.llm_provider,
        "llm_model": settings.model_name,
    }
    generate_phase1_report(
        report_path=settings.paths.baseline_report,
        source_summary=source_summary, metrics=metrics,
        quality=quality, freshness=freshness,
    )

    print("\n" + "=" * 60)
    print("BASELINE COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()
