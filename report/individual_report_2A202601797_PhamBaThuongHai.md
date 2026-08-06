# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin | Nội dung |
|-----------|----------|
| Họ và tên | Phạm Bá Thượng Hải |
| MSSV | 2A202601797 |
| Khóa/Lớp | K3 |
| Tên nhóm | Nhóm 4 |
| Vai trò chính | Vai trò 4 — Evaluation & observability |
| Repository | https://github.com/VinUni-AI20k/K3_Day10_Data-Pipeline-Data-Observability |
| Ngày hoàn thành | 2026-08-06 |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
|--------------------|-------------------|---------------|-----------------|------------|
| Evaluation test set | `src/evaluation/testset.py` -> `build_test_set()` | `papers_clean.csv` | `data/eval/test_set.json` (18 câu hỏi) | Hoàn thành |
| LLM-based evaluation | `src/evaluation/metrics.py` -> `evaluate_pipeline()` | Test set + embedding index | `baseline_metrics.json`, `baseline_answers.json` | Hoàn thành |
| Data quality checks | `src/observability/quality.py` -> `run_data_quality_checks()`, `build_freshness_report()` | Clean DataFrame + Settings | `baseline_quality.json`, `freshness_report.json` | Hoàn thành |
| Reporting | `src/observability/reporting.py` -> `generate_phase1_report()`, `generate_corruption_report()` | Metrics, quality, freshness | `phase1_report.md`, `corruption_report.md` | Hoàn thành |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả |
|-----------|------------------------------|---------|
| Fix LLM evaluation (F1 luôn = 1.0) | Module `metrics.py` (code gốc dùng rule-based) | Sửa thành LLM-based RAG -> F1 realistic (0.18) |
| Fix NaN handling trong testset | `testset.py` — xử lý `categories_joined` null | Thêm `_safe_str()` để convert NaN -> empty string |
| Fix API token limit | `metrics.py` — OpenRouter yêu cầu 65535 tokens | Thêm `max_tokens=256` cho LLM calls |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
|------------------------|----------------------------|------------------|---------------|
| Build test set từ clean data | `testset.py` | `data/eval/test_set.json` — 18 câu hỏi (6 summary, 6 authors, 6 date) | Kiểm tra file JSON |
| Evaluate baseline với LLM | `metrics.py` | `baseline_metrics.json` — F1=0.1809, hit_rate=1.0 | Kiểm tra file JSON |
| Quality checks 6 dimensions | `quality.py` | `baseline_quality.json` — 6/6 PASSED | Kiểm tra file JSON |
| Run corruption flow evaluation | `metrics.py` | 3 bộ metrics (baseline/corrupted/repaired) | `python script/run_corruption_flow.py` |
| Generate reports | `reporting.py` | `phase1_report.md`, `corruption_report.md` | Đọc file Markdown |

Artifact chính: **Bộ số liệu 3 trạng thái** (baseline/corrupted/repaired) chứng minh data corruption ảnh hưởng RAG quality và repair phục hồi được metrics.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Vai trò 4 chịu trách nhiệm xây dựng **hệ thống evaluation end-to-end** cho RAG pipeline: từ việc tạo bộ test, chạy evaluation qua LLM, kiểm tra chất lượng dữ liệu, cho đến sinh báo cáo so sánh 3 trạng thái.

Vấn đề kỹ thuật quan trọng nhất: code gốc dùng **rule-based lookup** (`qa.py`) trả về đúng metadata -> `token_f1` luôn = 1.0. Cần chuyển sang **LLM-based RAG** để evaluation phản ánh thực tế.

### Cách triển khai

**Evaluation pipeline (sửa `metrics.py`):**
1. **Retrieval**: Dùng `answer_question()` để tìm documents liên quan qua embedding search + exact title match
2. **Answer generation**: Gửi top-2 contexts vào LLM với prompt RAG -> LLM sinh câu trả lời tự nhiên
3. **Scoring**: Tính `token_f1` giữa LLM answer và ground_truth, đồng thời dùng LLM judge chấm điểm 1-5
4. **Fallback**: Nếu LLM fail -> dùng heuristic (F1 >= 0.95 -> score 5, F1 >= 0.5 -> score 3, else 1)

**LLM judge fix:**
- `with_structured_output()` không kế thừa `max_tokens` -> gửi 65535 -> 402 error
- Fix: gọi LLM trực tiếp với `max_tokens=512`, parse JSON response thủ công thành `JudgeVerdict`

**Quality checks (`quality.py`):**
6 checks trên 3 dimensions:
- Completeness: row_count, paper_id_not_null, title_not_null, summary_not_empty
- Uniqueness: paper_id_unique
- Timeliness: freshness (age_days <= 180)

### Input, output và contract

| Thành phần | Mô tả |
|-----------|-------|
| Input | `papers_clean.csv` (24 rows, 14 cols), embedding index, Settings |
| Output | `test_set.json`, `baseline_metrics.json`, `baseline_answers.json`, quality JSONs, report MDs |
| Module phụ thuộc | `retrieval/index.py` (embedding), `retrieval/llm.py` (LLM builder), `retrieval/qa.py` (retrieval) |
| Điều kiện lỗi | NaN trong `categories_joined`, API credits hết (402), LLM judge silent fallback |

### Cách xác minh

```bash
# Chạy baseline
python script/run_phase1.py

# Verify không có F1 = 1.0
python -c "import json; a=json.load(open('data/results/baseline_answers.json')); print(all(x['token_f1']<1.0 for x in a))"

# Verify không có fallback judge
python -c "import json; a=json.load(open('data/results/baseline_answers.json')); print(sum(1 for x in a if 'Fallback' in x['judge']['reasoning']), 'fallback')"
```

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Code gốc `metrics.py` dùng `answer_question()` (rule-based lookup từ `qa.py`) -> answer luôn = exact metadata -> `token_f1` luôn = 1.0. Checkpoint yêu cầu F1 không bao giờ đạt 1.0.
- **Các phương án:**
  1. Giữ rule-based: nhanh, không tốn API credits, nhưng F1 = 1.0 không phản ánh thực tế RAG.
  2. Dùng LLM-based RAG: gửi retrieved contexts vào LLM để sinh answer -> F1 realistic, nhưng tốn API credits.
- **Phương án đã chọn:** LLM-based RAG (phương án 2).
- **Lý do:** Checkpoint yêu cầu F1 < 1.0. LLM paraphrase answer, không copy exact metadata -> metrics có ý nghĩa.
- **Bằng chứng:** Baseline `mean_token_f1 = 0.1809` (không còn 1.0), tất cả 54 answers trong 3 phases đều có F1 < 1.0.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng:** `openai.APIStatusError: Error code: 402 - You requested up to 65535 tokens, but can only afford 15217.`
- **Nguyên nhân gốc:** `with_structured_output()` trong LangChain tạo request mới không kế thừa `max_tokens=1024` từ `build_llm()`. OpenRouter mặc định yêu cầu 65535 tokens. Exception bị catch silently -> fallback heuristic -> F1 vẫn trông có vẻ hợp lý nhưng không có real LLM evaluation.
- **Cách xử lý:**
  1. Thay `with_structured_output()` bằng gọi LLM trực tiếp với `max_tokens=512`
  2. Parse JSON response thủ công thành `JudgeVerdict`
  3. Giảm contexts từ 3 -> 2 để giảm prompt size
- **Cách xác minh:** Chạy lại pipeline -> 18/18 câu đều qua LLM judge thật (0 fallback).
- **Điều học được:** Không nên catch exception silently. Ít nhất phải log warning khi fallback.

## 7. Hiểu biết về luồng end-to-end

**1. Dữ liệu đi từ Crossref đến vector index như thế nào?**

Crossref API -> `fetch_source_records()` lấy raw JSON -> `parse_crossref_payload()` parse thành PaperRecord -> `build_clean_dataframe()` clean (normalize, dedupe, tạo `text_for_embedding` = title + summary + authors) -> `LocalEmbeddingIndex.build()` encode MiniLM-L6-v2 -> ChromaDB collection.

**2. Evaluation set và ground-truth document IDs dùng để đo retrieval/answer quality ra sao?**

Test set 18 câu hỏi, mỗi câu có `ground_truth` (expected answer) và `ground_truth_doc_ids` (DOI). `retrieval_hit_rate` = tỷ lệ câu mà top-K chứa đúng DOI. `token_f1` = token-level F1. `judge` = LLM chấm 1-5 so sánh answer với ground_truth.

**3. Quality checks khác freshness monitoring ở điểm nào?**

Quality checks kiểm tra tính đúng đắn cấu trúc (completeness: không null/empty; uniqueness: không duplicate). Freshness kiểm tra tính kịp thời: `age_days` vượt ngưỡng 180 ngày. Quality bắt corruption kiểu blank/duplicate, freshness bắt corruption kiểu stale dates.

**4. Vì sao phải dùng cùng test set cho baseline, corrupted và repaired?**

Để so sánh công bằng. Nếu dùng test set khác -> không thể kết luận thay đổi metrics là do data corruption hay do câu hỏi khác.

**5. Repair được xem là thành công dựa trên artifact và metric nào?**

Repair thành công khi: `repaired_metrics.json` gần baseline; `repaired_quality.json` 6/6 PASSED (vs 3/6 corrupted); freshness FRESH (vs STALE corrupted). Thực tế: hit_rate phục hồi 1.0, judge_score phục hồi 3.5, quality 6/6.

## 8. Phân tích kết quả

### Metrics chính

| Metric/signal | Baseline | Corrupted | Repaired | Nhận xét của cá nhân |
|---------------|----------|-----------|----------|---------------------|
| `retrieval_hit_rate` | 1.0000 | 0.8333 | 1.0000 | Corruption làm 3/18 câu tìm sai doc; repair phục hồi 100% |
| `mean_token_f1` | 0.1809 | 0.1440 | 0.1773 | Giảm 20% khi corrupt, phục hồi 98% khi repair |
| `judge_accuracy` | 0.6667 | 0.5556 | 0.6667 | Judge nghiêm khắc hơn với corrupted data |
| `mean_judge_score` | 3.5000 | 3.2222 | 3.5000 | Phục hồi hoàn toàn — repair effective |
| Quality checks | 6/6 | 3/6 | 6/6 | 3 checks fail: summary_empty, uniqueness, freshness |
| Freshness status | FRESH | STALE | FRESH | 5 stale rows do inject date 2020-01-01 |

### Kết luận từ số liệu

**Chuỗi 1 — Corruption:** Data corruption (blank summary + stale dates + duplicates) -> quality checks fail 3/6, freshness STALE -> retrieval_hit_rate giảm 16.7%, token_f1 giảm 20%.

**Chuỗi 2 — Repair:** Re-clean từ raw source -> quality 6/6 PASSED, freshness FRESH -> metrics phục hồi gần 100%.

**Kết quả khác kỳ vọng:** `mean_token_f1` repaired (0.1773) không phục hồi hoàn toàn về baseline (0.1809). Nguyên nhân: LLM nondeterministic — cùng prompt nhưng answer khác wording. Đã kiểm tra: retrieval đúng cùng documents.

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất

1. **Silent fallback nguy hiểm:** `except Exception` catch tất cả lỗi và fallback không log -> metrics trông hợp lý nhưng không có real evaluation. Phải ít nhất log warning.

2. **Quality checks là hệ thống cảnh báo sớm:** 6 dimensions bắt được 6 loại corruption khác nhau. Chạy quality trước evaluation giúp phát hiện data xấu sớm.

3. **LLM provider quirks:** Mỗi provider có giới hạn khác nhau (max_tokens, rate limit, structured output). Cần test riêng từng provider, không giả định hoạt động giống nhau.

### Nếu có thêm thời gian

Bổ sung `published` date vào `text_for_embedding` để LLM trả lời được date questions. Hiện tại 6/6 date questions đều fail (F1 = 0.0) vì context không chứa date.

## 10. Cam kết của thành viên

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi "đã chạy thành công" cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Phạm Bá Thượng Hải
**Ngày xác nhận:** 2026-08-06
