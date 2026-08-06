# Báo cáo Phase 2 — Corruption & Repair

## 1. Corruption Scenarios

Pipeline corruption áp dụng 6 loại lỗi lên clean dataset (seed=42), mỗi loại ảnh hưởng 4 records:

| Loại corruption | Mô tả | Số record | Quality signal bị ảnh hưởng |
|-----------------|--------|-----------|----------------------------|
| Drop latest records | Xóa 4 bài mới nhất khỏi dataset | 4 | completeness (row_count giảm) |
| Blank summary | Xóa trắng nội dung abstract | 4 | completeness (summary_not_empty fail) |
| Inject noise | Chèn text nhiễu vào summary | 4 | validity (embedding quality giảm) |
| Truncate title | Cắt ngắn tiêu đề | 4 | validity (retrieval by title fail) |
| Stale dates | Đổi ngày xuất bản thành 2020-01-01 | 4 | timeliness (freshness fail) |
| Duplicate rows | Nhân đôi 4 records | 4 | uniqueness (paper_id_unique fail) |

Artifact: `data/results/corruption_log.json`

## 2. So sánh Metrics: Baseline vs Corrupted vs Repaired

| Metric | Baseline | Corrupted | Repaired | Thay đổi (Corrupt) | Phục hồi (Repair) |
|--------|----------|-----------|----------|--------------------|--------------------|
| `retrieval_hit_rate` | 1.0000 | 0.8333 | 1.0000 | -16.67% | +16.67% (100%) |
| `mean_token_f1` | 0.1809 | 0.1440 | 0.1773 | -20.40% | +23.13% (98%) |
| `judge_accuracy` | 0.6667 | 0.5556 | 0.6667 | -16.67% | +16.67% (100%) |
| `mean_judge_score` | 3.5000 | 3.2222 | 3.5000 | -7.94% | +7.94% (100%) |

Artifact: `data/results/baseline_metrics.json`, `data/results/corrupted_metrics.json`, `data/results/repaired_metrics.json`

## 3. Quality Checks Comparison

| Check | Baseline | Corrupted | Repaired |
|-------|----------|-----------|----------|
| row_count | PASSED | PASSED | PASSED |
| paper_id_not_null | PASSED | PASSED | PASSED |
| paper_id_unique | PASSED | **FAILED** | PASSED |
| title_not_null | PASSED | PASSED | PASSED |
| summary_not_empty | PASSED | **FAILED** | PASSED |
| freshness | PASSED | **FAILED** | PASSED |
| **Tổng** | **6/6** | **3/6** | **6/6** |

## 4. Freshness Comparison

| Thuộc tính | Baseline | Corrupted | Repaired |
|------------|----------|-----------|----------|
| Trạng thái | FRESH | **STALE** | FRESH |
| Stale rows | 0 | 5 | 0 |

## 5. Phân tích nhân quả

### Chuỗi 1 — Tác động của Corruption

**Nguyên nhân**: Drop 4 bài mới nhất + blank 4 summary + stale 4 dates + duplicate 4 rows

**Hệ quả**:
- Quality checks fail 3/6: `summary_not_empty` (4 blank), `paper_id_unique` (4 duplicate), `freshness` (5 stale rows)
- `retrieval_hit_rate` giảm 16.67%: 3/18 câu hỏi không tìm được document gốc (do bài bị drop hoặc summary bị blank làm embedding kém)
- `token_f1` giảm 20.40%: câu trả lời sai do context bị nhiễu hoặc thiếu
- `judge_score` giảm từ 3.5 xuống 3.22: LLM judge nhận ra câu trả lời kém chính xác hơn

### Chuỗi 2 — Hiệu quả của Repair

**Hành động**: Re-clean từ raw source gốc (`crossref_records.json`), rebuild embedding index

**Hệ quả**:
- Quality checks phục hồi 6/6 PASSED
- Freshness phục hồi FRESH (0 stale rows)
- `retrieval_hit_rate` phục hồi 1.0 (100%)
- `judge_score` phục hồi 3.5 (100%)
- `token_f1` phục hồi 98% (0.1773 vs 0.1809) — chênh lệch 2% do LLM nondeterministic

### Corruption ảnh hưởng rõ nhất

**Drop latest records + blank summary** có tác động lớn nhất: gây retrieval miss trực tiếp (3 câu hỏi tìm sai document) và làm context trống/thiếu cho LLM.

### Kết quả khác kỳ vọng

`mean_token_f1` repaired (0.1773) không phục hồi hoàn toàn về baseline (0.1809). Nguyên nhân: LLM có tính nondeterministic — cùng prompt nhưng sinh câu trả lời khác wording giữa 2 lần chạy. Đã kiểm tra: retrieval tìm đúng cùng documents, chỉ LLM output khác từ ngữ.

## 6. Kết luận

1. Data corruption ảnh hưởng trực tiếp và đo lường được đến chất lượng RAG pipeline.
2. Repair từ raw source gốc khôi phục được gần 100% metrics, chứng minh tầm quan trọng của việc lưu trữ dữ liệu nguồn.
3. Quality checks tự động (6 dimensions) là hệ thống cảnh báo sớm hiệu quả — phát hiện corruption trước khi user nhận câu trả lời sai.
