from __future__ import annotations

from core.config import load_settings
from core.utils import now_utc, read_json, write_csv, write_json
from evaluation.metrics import evaluate_pipeline
from evaluation.testset import build_test_set
from ingestion.cleaning import build_clean_dataframe
from ingestion.crossref import fetch_source_records, load_raw_records
from observability.quality import build_freshness_report, run_data_quality_checks
from observability.reporting import generate_phase1_report
from retrieval.index import LocalEmbeddingIndex


def main() -> None:
    """Build the baseline pipeline end-to-end."""
    print("=" * 60)
    print("PHASE 1 — Baseline Pipeline")
    print("=" * 60)

    settings = load_settings()
    run_date = now_utc()
    print(f"\n[1/9] Settings loaded (provider={settings.llm_provider}, model={settings.model_name})")

    # 2. Load or fetch raw records
    print("\n[2/9] Loading raw records...")
    if settings.paths.raw_records_json.exists() and not settings.refresh_source:
        print(f"  Using cached records from {settings.paths.raw_records_json}")
        records = load_raw_records(settings.paths.raw_records_json)
    else:
        print(f"  Fetching from Crossref API (query='{settings.source_query[:50]}...')")
        records = fetch_source_records(settings)
    print(f"  Total raw records: {len(records)}")

    # 3. Clean data
    print("\n[3/9] Cleaning data...")
    df = build_clean_dataframe(records, run_date)
    print(f"  Cleaned records: {len(df)}")

    # 4. Save clean CSV/JSON
    print("\n[4/9] Saving clean data...")
    write_csv(df, settings.paths.clean_csv)
    print(f"  CSV -> {settings.paths.clean_csv}")
    clean_records = df.to_dict(orient="records")
    write_json(settings.paths.clean_json, clean_records)
    print(f"  JSON -> {settings.paths.clean_json}")

    # 5. Build embedding index
    print("\n[5/9] Building embedding index...")
    index = LocalEmbeddingIndex.build(df=df, settings=settings, embeddings_output_path=settings.paths.embeddings_json)
    print(f"  Index built: {len(df)} documents in collection '{index.collection_name}'")

    # 6. Generate or load evaluation set
    print("\n[6/9] Building evaluation test set...")
    if settings.paths.eval_testset.exists() and not settings.refresh_test_set:
        print(f"  Using cached test set from {settings.paths.eval_testset}")
        test_set = read_json(settings.paths.eval_testset)
    else:
        test_set = build_test_set(df, settings.paths.eval_testset)
    print(f"  Test set: {len(test_set)} questions")

    # 7. Evaluate
    print("\n[7/9] Evaluating baseline...")
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

    # 8. Quality checks + freshness
    print("\n[8/9] Running data quality checks...")
    quality = run_data_quality_checks(df, settings, report_name="baseline_quality")
    freshness = build_freshness_report(df, settings, settings.paths.freshness_report)

    # 9. Generate report
    print("\n[9/9] Generating phase 1 report...")
    source_summary = {
        "source": settings.source_api, "query": settings.source_query,
        "filter": settings.source_filter, "max_results": settings.max_results,
        "records_fetched": len(records), "records_after_cleaning": len(df),
        "embedding_model": settings.embedding_model,
        "llm_provider": settings.llm_provider, "llm_model": settings.model_name,
    }
    generate_phase1_report(report_path=settings.paths.baseline_report, source_summary=source_summary, metrics=metrics, quality=quality, freshness=freshness)

    print("\n" + "=" * 60)
    print("PHASE 1 COMPLETE")
    print("=" * 60)
    print(f"\nArtifacts generated:")
    print(f"  Raw data:        {settings.paths.raw_api_response.parent}")
    print(f"  Clean data:      {settings.paths.clean_csv.parent}")
    print(f"  Embeddings:      {settings.paths.embeddings_json}")
    print(f"  Test set:        {settings.paths.eval_testset}")
    print(f"  Metrics:         {settings.paths.baseline_metrics}")
    print(f"  Quality:         {settings.paths.quality_dir}")
    print(f"  Report:          {settings.paths.baseline_report}")
