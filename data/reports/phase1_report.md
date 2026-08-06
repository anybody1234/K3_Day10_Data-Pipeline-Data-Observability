# Báo cáo Phase 1 — Baseline Pipeline

## 1. Tổng quan nguồn dữ liệu

| Thông tin | Chi tiết |
|-----------|----------|
| Nguồn | Crossref REST API (`https://api.crossref.org/works`) |
| Query | `agentic retrieval augmented generation large language model` |
| Filter | `from-pub-date:2026-02-07`, `has-abstract:true` |
| Số record lấy về | 24 (`max_results=24` trong config) |
| Embedding model | `sentence-transformers/all-MiniLM-L6-v2` |
| LLM provider | OpenAI (gpt-4o-mini) |
| Records sau cleaning | 24 (không mất record nào) |

## 2. Evaluation Metrics

| Metric | Giá trị | Diễn giải |
|--------|---------|-----------|
| `samples` | 18 | 6 bài x 3 loại câu hỏi (summary, authors, date) |
| `retrieval_hit_rate` | 1.0000 | 100% câu hỏi tìm đúng document gốc trong top-K |
| `mean_token_f1` | 0.1809 | Token F1 thấp do LLM paraphrase, không copy exact metadata |
| `judge_accuracy` | 0.6667 | 12/18 câu được LLM judge đánh giá đúng |
| `mean_judge_score` | 3.5000 | Điểm trung bình 3.5/5 — câu trả lời đúng nội dung nhưng diễn đạt khác |

> RAGAS: Chưa bật (`RUN_RAGAS=1` để kích hoạt).
>
> LLM judge: gpt-4o-mini (18/18 real judge, 0 fallback heuristic).

**Nhận xét**: `retrieval_hit_rate = 1.0` cho thấy embedding index hoạt động tốt — MiniLM-L6-v2 kết hợp exact title matching tìm đúng 100% documents. `token_f1 = 0.18` thấp là bình thường vì LLM sinh câu trả lời tự nhiên, không copy nguyên văn ground truth. `judge_score = 3.5` phản ánh câu trả lời đúng ý nhưng date questions thường fail (context không chứa ngày xuất bản).

## 3. Data Quality Checks

**Kết quả**: 6/6 PASSED

| Check | Dimension | Kết quả | Kỳ vọng | Thực tế |
|-------|-----------|---------|---------|---------|
| row_count | completeness | PASSED | >= 1 | 24 |
| paper_id_not_null | completeness | PASSED | 0 nulls | 0 nulls |
| paper_id_unique | uniqueness | PASSED | 0 duplicates | 0 duplicates |
| title_not_null | completeness | PASSED | 0 null/empty | 0 null/empty |
| summary_not_empty | completeness | PASSED | 0 empty | 0 empty |
| freshness | timeliness | PASSED | 0 stale rows | 0 stale rows (0.0%) |

Artifact: `data/quality/baseline_quality.json`

## 4. Freshness

| Thuộc tính | Giá trị |
|------------|---------|
| Trạng thái | FRESH |
| Bài mới nhất | 2026-08-01 |
| Bài cũ nhất | 2026-02-12 |
| Số bài quá hạn | 0/24 |
| Ngưỡng freshness | 180 ngày |

Artifact: `data/quality/freshness_report.json`

## 5. Artifact Checklist

| Artifact | Đường dẫn | Trạng thái |
|----------|-----------|------------|
| Raw API response | `data/raw/crossref_response.json` | Co |
| Raw records | `data/raw/crossref_records.json` | Co |
| Clean CSV | `data/clean/papers_clean.csv` | Co |
| Clean JSON | `data/clean/papers_clean.json` | Co |
| Embedding manifest | `data/embeddings/papers_embeddings.json` | Co |
| Test set | `data/eval/test_set.json` | Co |
| Baseline metrics | `data/results/baseline_metrics.json` | Co |
| Baseline answers | `data/results/baseline_answers.json` | Co |
| Quality checks | `data/quality/baseline_quality.json` | Co |
| Freshness report | `data/quality/freshness_report.json` | Co |
| Phase 1 report | `data/reports/phase1_report.md` | Co |
