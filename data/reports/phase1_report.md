# Phase 1 — Baseline Report

## 1. Source Summary

- **source**: teammate_clean_data
- **records_after_cleaning**: 24
- **embedding_model**: sentence-transformers/all-MiniLM-L6-v2
- **llm_provider**: openrouter
- **llm_model**: google/gemini-2.5-flash

## 2. Evaluation Metrics

| Metric | Value |
|--------|-------|
| `samples` | 18 |
| `retrieval_hit_rate` | 1.0000 |
| `mean_token_f1` | 0.1460 |
| `judge_accuracy` | 0.0556 |
| `mean_judge_score` | 1.1111 |

> RAGAS: Set RUN_RAGAS=1 to enable the slower Ragas pass.

## 3. Data Quality

**Overall**: ✅ ALL PASSED (6/6)

| Check | Dimension | Passed | Expected | Actual |
|-------|-----------|--------|----------|--------|
| row_count | completeness | ✅ | >= 1 | 24 |
| paper_id_not_null | completeness | ✅ | 0 nulls | 0 nulls |
| paper_id_unique | uniqueness | ✅ | 0 duplicates | 0 duplicates |
| title_not_null | completeness | ✅ | 0 null/empty | 0 null/empty |
| summary_not_empty | completeness | ✅ | 0 empty summaries | 0 empty |
| freshness | timeliness | ✅ | 0 rows older than 180 days | 0 stale rows (0.0%) |

## 4. Freshness

**Status**: 🟢 FRESH

- Latest published: 2026-08-01
- Oldest published: 2026-02-12
- Stale rows: 0/24
- Threshold: 180 days
- Reason: All records within freshness threshold
