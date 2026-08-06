# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin         | Nội dung                  |
| ------------------ | -------------------------- |
| Họ và tên       | [Họ và tên]             |
| MSSV               | [MSSV]                     |
| Khóa/Lớp         | K3                         |
| Tên nhóm         | [Tên nhóm]               |
| Vai trò chính    | Vai trò 3 — RAG & Agent Owner |
| Repository         | https://github.com/VinUni-AI20k/K3_Day10_Data-Pipeline-Data-Observability |
| Ngày hoàn thành | 2026-08-06                 |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao  | Trạng thái |
| ------------------ | --------------------- | ---------------- | ----------------- | ------------ |
| Evaluation test set | `src/evaluation/testset.py` → `build_test_set()` | `papers_clean.csv` (từ VT2) | `data/eval/test_set.json` (18 câu hỏi) | Hoàn thành |
| LLM-based evaluation | `src/evaluation/metrics.py` → `evaluate_pipeline()` | Test set + embedding index | `baseline_metrics.json`, `baseline_answers.json` | Hoàn thành |
| Data quality checks | `src/observability/quality.py` → `run_data_quality_checks()`, `build_freshness_report()` | Clean DataFrame + Settings | `baseline_quality.json`, `freshness_report.json` | Hoàn thành |
| Reporting | `src/observability/reporting.py` → `generate_phase1_report()`, `generate_corruption_report()` | Metrics, quality, freshness | `phase1_report.md`, `corruption_report.md` | Hoàn thành |
| Phase 1 pipeline | `src/pipelines/phase1.py` → `main()` | Raw records + Settings | Toàn bộ baseline artifacts | Hoàn thành |
| Corruption simulation | `src/ingestion/corruption.py` → `corrupt_clean_dataframe()` | Clean DataFrame | `papers_clean_corrupted.csv`, `corruption_log.json` | Hoàn thành |
| Phase 2 pipeline | `src/pipelines/corruption_flow.py` → `main()` | Baseline artifacts | Corrupted + Repaired artifacts | Hoàn thành |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả |
| ---------- | ------------------------------ | -------- |
| Fix LLM evaluation (F1 luôn = 1.0) | Module `metrics.py` (code gốc dùng rule-based) | Sửa thành LLM-based RAG → F1 realistic (0.18) |
| Fix NaN handling trong testset | `testset.py` — xử lý `categories_joined` null | Thêm `_safe_str()` để convert NaN → empty string |
| Fix API token limit | `metrics.py` — OpenRouter yêu cầu 65535 tokens | Thêm `max_tokens=256` cho LLM calls |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| ----------------------- | ----------------------------- | ------------------- | --------------- |
| Build test set từ clean data | `testset.py` | `data/eval/test_set.json` — 18 câu hỏi (6 summary, 6 authors, 6 date) | `python script/run_baseline_from_clean.py` |
| Evaluate baseline với LLM | `metrics.py` | `baseline_metrics.json` — F1=0.1809, hit_rate=1.0 | Kiểm tra file JSON |
| Quality checks 6 dimensions | `quality.py` | `baseline_quality.json` — 6/6 PASSED | Kiểm tra file JSON |
| Run corruption flow | `corruption_flow.py` | 3 bộ metrics + corruption_log + comparison report | `python script/run_corruption_flow.py` |

Artifact chính: **Bộ số liệu 3 trạng thái** (baseline/corrupted/repaired) chứng minh data corruption ảnh hưởng RAG quality và repair phục hồi được metrics.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Vai trò 3 chịu trách nhiệm xây dựng **hệ thống evaluation end-to-end** cho RAG pipeline: từ việc tạo bộ test, chạy evaluation qua LLM, kiểm tra chất lượng dữ liệu, cho đến sinh báo cáo so sánh 3 trạng thái (baseline → corrupted → repaired).

Vấn đề kỹ thuật quan trọng nhất: code gốc dùng **rule-based lookup** (`qa.py`) trả về đúng metadata → `token_f1` luôn = 1.0. Cần chuyển sang **LLM-based RAG** để evaluation phản ánh thực tế.

### Cách triển khai

**Evaluation pipeline (sửa `metrics.py`):**
1. **Retrieval**: Dùng `answer_question()` để tìm documents liên quan qua embedding search + exact title match
2. **Answer generation (mới)**: Gửi top-2 contexts vào LLM với prompt RAG → LLM sinh câu trả lời tự nhiên
3. **Scoring**: Tính `token_f1` giữa LLM answer và ground_truth, đồng thời dùng LLM judge chấm điểm 1-5
4. **Fallback**: Nếu LLM fail (hết credits, timeout) → dùng rule-based answer

**Corruption simulation (`corruption.py`):**
Áp 6 loại corruption lên clean data:
1. Drop latest records (mất dữ liệu mới)
2. Blank summary (mất nội dung)
3. Inject noise text (nhiễu)
4. Truncate titles (cắt tiêu đề)
5. Stale dates (ngày cũ → fail freshness)
6. Duplicate rows (vi phạm uniqueness)

### Input, output và contract

| Thành phần | Mô tả |
| ---------- | ------- |
| Input | `papers_clean.csv` (24 rows, 14 cols) từ VT2; `crossref_records.json` (raw) từ VT2 |
| Output | `test_set.json`, `baseline_metrics.json`, `baseline_answers.json`, quality JSONs, report MDs |
| Module phụ thuộc | `retrieval/index.py` (embedding), `retrieval/llm.py` (LLM builder), `retrieval/qa.py` (retrieval) |
| Module sử dụng output | VT4 (Great Expectations), báo cáo nhóm |
| Điều kiện lỗi cần xử lý | NaN trong `categories_joined`, API credits hết (402), timezone mismatch |

### Cách xác minh

```bash
# Chạy baseline
python script/run_baseline_from_clean.py

# Chạy corruption flow
python script/run_corruption_flow.py

# Verify không có F1 = 1.0
grep -r "token_f1.*1.0" data/results/
```

- **Kết quả mong đợi:** Tất cả `token_f1` < 1.0; corrupted metrics giảm so với baseline; repaired phục hồi gần baseline.
- **Kết quả thực tế:** Đúng như mong đợi (xem bảng Section 8).
- **Artifact:** `data/results/baseline_metrics.json`, `data/results/corrupted_metrics.json`, `data/results/repaired_metrics.json`

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Code gốc `metrics.py` dùng `answer_question()` (rule-based lookup từ `qa.py`) → answer luôn = exact metadata → `token_f1` luôn = 1.0. Checkpoint C3 yêu cầu F1 không bao giờ đạt 1.0.
- **Các phương án đã cân nhắc:**
  1. **Giữ rule-based**: Nhanh, không tốn API credits, nhưng F1 = 1.0 không phản ánh thực tế RAG.
  2. **Dùng LLM-based RAG**: Gửi retrieved contexts vào LLM để sinh answer → F1 realistic, nhưng tốn API credits và chậm hơn.
- **Phương án đã chọn:** LLM-based RAG (phương án 2).
- **Lý do:** Checkpoint yêu cầu F1 < 1.0. Đây là cách duy nhất phản ánh đúng chất lượng RAG thực tế — LLM paraphrase answer, không copy exact metadata. Trade-off: tốn ~36 API calls/phase nhưng metrics có ý nghĩa.
- **Bằng chứng:** Baseline `mean_token_f1 = 0.1809` (không còn 1.0), tất cả 54 answers trong 3 phases đều có F1 < 1.0.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng:** `openai.APIStatusError: Error code: 402 - This request requires more credits, or fewer max_tokens. You requested up to 65535 tokens, but can only afford 15217.`
- **Lệnh tái hiện:** `python script/run_baseline_from_clean.py` (khi dùng OpenRouter key hết credits)
- **Nguyên nhân gốc:** OpenRouter mặc định yêu cầu `max_tokens=65535` cho model Gemini 2.5 Flash. Khi tài khoản không đủ credits, API trả 402. Đồng thời, exception bị catch silently trong `metrics.py` → fallback về rule-based → F1 vẫn = 1.0 mà không có warning.
- **Cách xử lý:**
  1. Thêm `max_tokens=256` vào `llm.invoke()` calls để giảm token yêu cầu
  2. Giảm contexts từ 3 → 2 để giảm prompt size
  3. Chuyển sang OpenAI `gpt-4o-mini` (rẻ hơn, ổn định hơn)
- **Cách xác minh:** Chạy lại pipeline → tất cả 18 câu đều qua LLM (không fallback), F1 = 0.1809.
- **Điều học được:** Luôn set `max_tokens` explicitly khi gọi API qua OpenRouter. Không nên catch exception silently — ít nhất phải log warning.

## 7. Hiểu biết về luồng end-to-end

**Câu trả lời:**

**1. Dữ liệu đi từ Crossref đến vector index như thế nào?**

Crossref API → `fetch_source_records()` lấy raw JSON → `parse_crossref_payload()` parse thành `PaperRecord` dataclass → `build_clean_dataframe()` clean (normalize whitespace, drop duplicates, tính `age_days`, tạo `text_for_embedding` = title + summary + authors) → `LocalEmbeddingIndex.build()` encode `text_for_embedding` qua MiniLM-L6-v2 thành vector 384d → lưu vào ChromaDB collection.

**2. Evaluation set và ground-truth document IDs dùng để đo retrieval/answer quality ra sao?**

Test set chứa 18 câu hỏi, mỗi câu có `ground_truth` (expected answer) và `ground_truth_doc_ids` (paper DOI). Khi evaluate: (a) `retrieval_hit_rate` = tỷ lệ câu hỏi mà top-K retrieved docs chứa đúng `ground_truth_doc_ids`; (b) `token_f1` = token-level F1 giữa LLM answer và `ground_truth`; (c) `judge` = LLM chấm điểm 1-5 so sánh answer với ground_truth.

**3. Quality checks khác freshness monitoring ở điểm nào?**

Quality checks kiểm tra **tính đúng đắn cấu trúc** dữ liệu (completeness: không null/empty; uniqueness: không duplicate). Freshness monitoring kiểm tra **tính kịp thời** (timeliness): bao nhiêu records có `age_days` vượt ngưỡng 180 ngày. Quality checks phát hiện corruption kiểu blank/duplicate, freshness phát hiện corruption kiểu stale dates.

**4. Vì sao phải dùng cùng test set cho baseline, corrupted và repaired?**

Để so sánh công bằng (apples-to-apples). Nếu mỗi phase dùng test set khác → không thể kết luận sự thay đổi metrics là do data corruption hay do câu hỏi khác. Cùng test set → mọi sự thay đổi đều phản ánh trực tiếp tác động của chất lượng dữ liệu lên RAG.

**5. Repair được xem là thành công dựa trên artifact và metric nào?**

Repair thành công khi: (a) `repaired_metrics.json` có metrics gần bằng hoặc bằng baseline; (b) `repaired_quality.json` cho 6/6 checks PASSED (vs 3/6 khi corrupted); (c) `repaired_freshness_report.json` hiện FRESH (vs STALE khi corrupted). Thực tế: retrieval_hit_rate phục hồi 1.0, judge_score phục hồi 3.5, quality 6/6 — repair thành công.

## 8. Phân tích kết quả

### Metrics chính

| Metric/signal          | Baseline | Corrupted | Repaired | Nhận xét của cá nhân |
| ---------------------- | -------: | --------: | -------: | ---------------------- |
| `retrieval_hit_rate` | 1.0000 | 0.8333 | 1.0000 | Corruption làm 3/18 câu tìm sai doc; repair phục hồi 100% |
| `mean_token_f1`      | 0.1809 | 0.1440 | 0.1773 | Giảm 20% khi corrupt, phục hồi 98% khi repair |
| `judge_accuracy`     | 0.6667 | 0.5556 | 0.6667 | Judge nghiêm khắc hơn với corrupted data |
| `mean_judge_score`   | 3.5000 | 3.2222 | 3.5000 | Phục hồi hoàn toàn — repair effective |
| Quality checks         | 6/6 ✅ | 3/6 ❌ | 6/6 ✅ | 3 checks fail: summary_empty, uniqueness, freshness |
| Freshness status       | FRESH 🟢 | STALE 🔴 | FRESH 🟢 | 5 stale rows do inject date 2020-01-01 |

### Kết luận từ số liệu

**Chuỗi 1 — Corruption:**
Data corruption (blank summary + stale dates + duplicates) → quality checks fail 3/6, freshness STALE → retrieval_hit_rate giảm 16.7%, token_f1 giảm 20%, judge giảm 8%.

**Chuỗi 2 — Repair:**
Repair từ raw source (re-clean) → quality 6/6 PASSED, freshness FRESH → retrieval_hit_rate phục hồi 1.0, token_f1 phục hồi 98%, judge_score phục hồi 100%.

**Corruption ảnh hưởng rõ nhất:** Drop latest records + blank summary → 3 câu hỏi không tìm được document gốc (retrieval miss), đồng thời summary trống làm context kém → LLM answer sai.

**Kết quả khác kỳ vọng:** `mean_token_f1` repaired (0.1773) không phục hồi hoàn toàn về baseline (0.1809). Giả thuyết: LLM có tính nondeterministic — cùng prompt nhưng answer khác nhau giữa 2 lần chạy. Đã kiểm tra: retrieval đúng cùng documents, chỉ LLM output khác wording → F1 dao động ±2% là bình thường.

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất

1. **Data pipeline:** Chất lượng dữ liệu đầu vào quyết định trực tiếp chất lượng output của RAG. Chỉ cần blank 4 summaries là đủ làm retrieval miss 16.7% và quality fail 50%.

2. **Data quality/observability:** Quality checks tự động (completeness, uniqueness, freshness) là "hệ thống cảnh báo sớm" — phát hiện corruption trước khi user nhận câu trả lời sai. 6 dimensions khác nhau bắt được 6 loại corruption khác nhau.

3. **Ảnh hưởng của data đến RAG agent:** `text_for_embedding` quyết định retrieval quality. Nếu trường quan trọng (published date) không nằm trong embedding text → LLM không thể trả lời câu hỏi liên quan, dù retrieval tìm đúng document. Thiết kế embedding schema cần cân nhắc kỹ query types.

### Nếu có thêm thời gian

Bổ sung `published` date vào `text_for_embedding` (format: `"Published: 2026-08-01"`) để LLM có thể trả lời date questions. Hiện tại 6/6 date questions đều fail (F1 = 0.0) vì context không chứa date. Cách đo: chạy lại evaluation → date question F1 tăng từ 0.0 lên > 0.5.

## 10. Cam kết của thành viên

Đánh dấu sau khi tự kiểm tra:

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi "đã chạy thành công" cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** [Họ và tên]
**Ngày xác nhận:** 2026-08-06
