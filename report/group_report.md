# Group Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin bài nộp

| Thông tin | Nội dung |
|-----------|----------|
| Khóa/Lớp | K3 |
| Tên nhóm | Nhóm 4 |
| Repository | https://github.com/VinUni-AI20k/K3_Day10_Data-Pipeline-Data-Observability |
| Ngày hoàn thành | 2026-08-06 |

### Thành viên và phân công

| STT | Họ và tên | MSSV | Vai trò chính | Module/deliverable sở hữu |
|----:|-----------|------|---------------|---------------------------|
| 1 | Lục Minh Đức | 2A202601918 | Vai trò 1 — Điều phối pipeline | `src/core/config.py`, `src/pipelines/phase1.py`, `src/pipelines/corruption_flow.py` |
| 2 | Phan Hoàng Long | 2A202601565 | Vai trò 2 — Nền tảng dữ liệu & recovery | `src/ingestion/crossref.py`, `src/ingestion/cleaning.py`, `src/ingestion/corruption.py` |
| 3 | Phạm Nguyên Việt | 2A202601547 | Vai trò 3 — RAG & agent | `src/retrieval/index.py`, `src/retrieval/embeddings.py`, `src/retrieval/qa.py`, `src/retrieval/llm.py` |
| 4 | Phạm Bá Thượng Hải | 2A202601797 | Vai trò 4 — Evaluation & observability | `src/evaluation/testset.py`, `src/evaluation/metrics.py`, `src/observability/quality.py`, `src/observability/reporting.py` |

## 2. Tóm tắt kết quả

Nhóm đã hoàn thành toàn bộ pipeline end-to-end: từ ingestion dữ liệu Crossref API (24 bài báo khoa học về RAG/LLM), cleaning và data modeling, xây dựng embedding index (MiniLM-L6-v2 + ChromaDB), tạo evaluation test set (18 câu hỏi), chạy baseline evaluation với LLM judge (gpt-4o-mini), kiểm tra data quality (6/6 PASSED) và freshness (FRESH).

Corruption flow áp dụng 6 loại lỗi có kiểm soát lên clean data: drop latest records, blank summary, inject noise, truncate title, stale dates, duplicate rows. Kết quả cho thấy corruption làm `retrieval_hit_rate` giảm 16.7%, `judge_score` giảm từ 3.5 xuống 3.22, quality checks fail 3/6.

Repair từ raw source gốc khôi phục gần 100% metrics: `retrieval_hit_rate` trở lại 1.0, `judge_score` phục hồi 3.5, quality 6/6 PASSED.

Blocker chính: OpenRouter free-tier giới hạn `max_tokens`, gây lỗi 402 cho LLM judge; đã fix bằng cách thêm `max_tokens` explicit và chuyển sang gpt-4o-mini.

## 3. Kiến trúc và luồng dữ liệu

### Luồng end-to-end

```text
Crossref API (24 records)
    -> raw response + raw records (data/raw/)
    -> cleaning: normalize, dedupe, text_for_embedding (data/clean/)
    -> embedding MiniLM-L6-v2 + ChromaDB index (data/embeddings/)
    -> evaluation test set 18 câu hỏi (data/eval/)
    -> baseline evaluation: retrieval + LLM RAG + LLM judge (data/results/)
    -> quality checks 6 dimensions + freshness (data/quality/)
    -> phase1 report (data/reports/)
    -> corruption 6 loại lên clean data
    -> re-index và re-evaluate corrupted
    -> repair từ raw source gốc
    -> re-index và re-evaluate repaired
    -> comparison report (data/reports/)
```

### Trách nhiệm của từng khối

| Khối | Input | Xử lý chính | Output/artifact | Owner |
|------|-------|-------------|-----------------|-------|
| Ingestion | Crossref API | Fetch với retry/backoff, parse JSON thành PaperRecord | `data/raw/crossref_response.json`, `data/raw/crossref_records.json` | Phan Hoàng Long |
| Cleaning | Raw records | Normalize whitespace, strip HTML, dedupe, tạo `text_for_embedding` | `data/clean/papers_clean.csv`, `data/clean/papers_clean.json` | Phan Hoàng Long |
| Embedding/index | Clean CSV | Encode MiniLM-L6-v2, lưu ChromaDB collection | `data/embeddings/papers_embeddings.json`, `data/chroma/` | Phạm Nguyên Việt |
| Evaluation | Test set + index | Retrieval + LLM RAG answer + LLM judge scoring | `data/results/baseline_metrics.json`, `data/results/baseline_answers.json` | Phạm Bá Thượng Hải |
| Observability | Clean DataFrame | Quality checks 6 dimensions, freshness monitoring | `data/quality/baseline_quality.json`, `data/quality/freshness_report.json` | Phạm Bá Thượng Hải |
| Corruption/repair | Clean data + raw source | 6 loại corruption, repair từ raw | `data/results/corruption_log.json`, corrupted/repaired artifacts | Phan Hoàng Long |
| Orchestration | Settings | Điều phối phase1.py và corruption_flow.py | `data/reports/phase1_report.md`, `data/reports/corruption_report.md` | Lục Minh Đức |

## 4. Cách tái hiện kết quả

### Cấu hình không chứa secret

| Biến/cấu hình | Giá trị sử dụng |
|----------------|-----------------|
| `LLM_PROVIDER` | openrouter / openai |
| `LLM_MODEL` | google/gemini-2.5-flash / gpt-4o-mini |
| Embedding model | sentence-transformers/all-MiniLM-L6-v2 |
| Số lượng Crossref records | 24 |
| Retrieval `top_k` | 4 |
| Freshness threshold | 180 ngày |
| Random seed | 42 (corruption) |

### Lệnh cài đặt

```bash
uv sync
```

Hoặc:

```bash
python -m pip install -e .
```

### Lệnh chạy

Baseline:

```bash
python script/run_phase1.py
```

Corruption flow:

```bash
python script/run_corruption_flow.py
```

### Kết quả tái hiện

| Lệnh | Trạng thái | Thời điểm chạy gần nhất | Bằng chứng |
|-------|-----------|-------------------------|------------|
| Baseline pipeline | Thành công | 2026-08-06 | `data/results/baseline_metrics.json`, `data/reports/phase1_report.md` |
| Corruption flow | Thành công | 2026-08-06 | `data/results/corrupted_metrics.json`, `data/reports/corruption_report.md` |

## 5. Ingestion, cleaning và data contract

### Nguồn dữ liệu

| Thuộc tính | Giá trị |
|------------|---------|
| Source | Crossref REST API (`https://api.crossref.org/works`) |
| Query/filter | `agentic retrieval augmented generation large language model`, `from-pub-date:2026-02-07`, `has-abstract:true` |
| Thời điểm lấy dữ liệu | 2026-08-06 |
| Số record nhận được | 24 |
| Cơ chế retry/backoff | 3 lần, backoff 2-4-8s, xử lý HTTP 429/503 và Timeout |

### Raw và clean schema

| Trường | Kiểu dữ liệu | Bắt buộc? | Ý nghĩa | Xử lý khi thiếu/sai |
|--------|-------------|-----------|---------|---------------------|
| `paper_id` | string | Có | DOI — khóa chính | Skip record nếu thiếu |
| `title` | string | Có | Tiêu đề bài báo | Skip record nếu rỗng |
| `summary` | string | Có | Abstract | Skip record nếu rỗng |
| `authors` | list[string] | Không | Danh sách tác giả | Để rỗng |
| `categories` | list[string] | Không | Chủ đề (subject) | Để rỗng (API không trả) |
| `published` | string | Không | Ngày xuất bản | Default 1 nếu thiếu month/day |
| `pdf_url` | string | Không | Link PDF | Để rỗng (33% thiếu) |

### Quy tắc cleaning

| Quy tắc | Quality dimension | Số record bị tác động | Cách xác minh |
|---------|-------------------|----------------------:|---------------|
| Strip HTML tags trong abstract | Validity | 24 (tất cả) | So sánh raw vs clean summary |
| Normalize whitespace | Validity | 24 | Kiểm tra không còn `\n`, `\t`, khoảng trắng thừa |
| Filter rows thiếu title/summary | Completeness | 0 (không record nào bị loại) | `len(raw) - len(clean)` = 0 |
| Deduplicate theo paper_id | Uniqueness | 0 (không trùng) | `df.paper_id.duplicated().sum()` = 0 |

`text_for_embedding` = `"{title}. {summary} Authors: {authors_joined}"` — kết hợp tiêu đề, tóm tắt và tác giả để embedding có đủ ngữ nghĩa cho retrieval.

`paper_id` = DOI từ Crossref — stable, unique, không thay đổi giữa các lần fetch.

`age_days` = `(run_date - published_date).days` — dùng để kiểm tra freshness.

## 6. Evaluation setup

| Thành phần | Cấu hình thực tế |
|------------|-----------------|
| Số câu hỏi | 18 |
| Các `question_type` | summary (6), authors (6), date (6) |
| Ground-truth document ID | `paper_id` (DOI) từ clean dataset |
| Embedding model | sentence-transformers/all-MiniLM-L6-v2 |
| Vector store/collection | ChromaDB `papers-baseline` |
| Retrieval `top_k` | 4 |
| LLM provider/model | OpenAI gpt-4o-mini |
| Test set dùng chung | `data/eval/test_set.json` (cố định cho cả 3 trạng thái) |

Test set được giữ nguyên khi đánh giá baseline, corrupted và repaired để đảm bảo so sánh công bằng (apples-to-apples). Nếu mỗi phase dùng test set khác, không thể kết luận sự thay đổi metrics là do data corruption hay do câu hỏi khác.

## 7. Kết quả baseline

### Artifact checklist

| Artifact | Đường dẫn thực tế | Trạng thái |
|----------|-------------------|------------|
| Raw response/records | `data/raw/crossref_response.json`, `data/raw/crossref_records.json` | Có |
| Cleaned dataset | `data/clean/papers_clean.csv`, `data/clean/papers_clean.json` | Có |
| Embedding manifest/index | `data/embeddings/papers_embeddings.json`, `data/chroma/` | Có |
| Evaluation set | `data/eval/test_set.json` | Có |
| Baseline metrics | `data/results/baseline_metrics.json` | Có |
| Quality/freshness | `data/quality/baseline_quality.json`, `data/quality/freshness_report.json` | Có |
| Baseline report | `data/reports/phase1_report.md` | Có |

### Baseline metrics

| Metric | Giá trị | Diễn giải |
|--------|---------|-----------|
| `retrieval_hit_rate` | 1.0000 | 100% câu hỏi tìm đúng document gốc trong top-4 |
| `mean_token_f1` | 0.1809 | Token F1 thấp do LLM paraphrase, không copy exact metadata |
| `judge_accuracy` | 0.6667 | 12/18 câu được LLM judge đánh giá đúng |
| `mean_judge_score` | 3.5000 | Điểm trung bình 3.5/5 |
| Ragas | N/A | Chưa bật (`RUN_RAGAS=1` để kích hoạt) |

## 8. Data quality và freshness

### Quality checks

| Check | Quality dimension | Ngưỡng/kỳ vọng | Kết quả baseline | Bằng chứng |
|-------|-------------------|----------------|-----------------|------------|
| row_count | completeness | >= 1 | PASSED (24) | `baseline_quality.json` |
| paper_id_not_null | completeness | 0 nulls | PASSED | `baseline_quality.json` |
| paper_id_unique | uniqueness | 0 duplicates | PASSED | `baseline_quality.json` |
| title_not_null | completeness | 0 null/empty | PASSED | `baseline_quality.json` |
| summary_not_empty | completeness | 0 empty | PASSED | `baseline_quality.json` |
| freshness | timeliness | 0 stale rows (180 ngày) | PASSED | `baseline_quality.json` |

### Freshness

| Thuộc tính | Giá trị |
|------------|---------|
| Freshness được đo tại | Clean dataset (`papers_clean.csv`) |
| Timestamp mới nhất | 2026-08-01 |
| Ngưỡng freshness | 180 ngày |
| Trạng thái baseline | FRESH |
| Lý do | Tất cả 24 records trong ngưỡng (max age = 175 ngày) |

## 9. Corruption scenarios và repair

| Corruption | Cách tạo | Record bị tác động | Quality signal kỳ vọng | Tác động thực tế | Cách repair |
|------------|---------|--------------------:|----------------------|------------------|-------------|
| Drop latest records | Xóa 4 bài mới nhất | 4 | completeness giảm | Retrieval miss 3 câu hỏi | Re-clean từ raw |
| Blank summary | Xóa trắng abstract | 4 | summary_not_empty fail | Embedding kém, answer sai | Re-clean từ raw |
| Inject noise | Chèn text nhiễu vào summary | 4 | Validity giảm | Token F1 giảm | Re-clean từ raw |
| Truncate title | Cắt ngắn tiêu đề | 4 | Retrieval by title fail | Exact lookup fail | Re-clean từ raw |
| Stale dates | Đổi published thành 2020-01-01 | 4 | freshness fail | 5 stale rows | Re-clean từ raw |
| Duplicate rows | Nhân đôi 4 records | 4 | paper_id_unique fail | Uniqueness violated | Re-clean từ raw |

Corruption log:

- Đường dẫn: `data/results/corruption_log.json`
- Trạng thái: Có
- Nhận xét: Log đầy đủ 6 loại corruption, ghi rõ paper_id bị tác động, seed=42, before/after count.

Repair thực hiện bằng cách chạy lại cleaning pipeline từ raw source gốc (`data/raw/crossref_records.json`), không sửa tay data hoặc metrics. Raw source không bị mutation trong quá trình corruption.

## 10. So sánh baseline, corrupted và repaired

| Metric/signal | Baseline | Corrupted | Repaired | Thay đổi do corruption | Mức phục hồi | Nhận xét |
|---------------|----------|-----------|----------|----------------------:|---------------:|----------|
| `retrieval_hit_rate` | 1.0000 | 0.8333 | 1.0000 | -16.67% | 100% | 3 câu hỏi tìm sai doc khi corrupt |
| `mean_token_f1` | 0.1809 | 0.1440 | 0.1773 | -20.40% | 98% | LLM nondeterministic gây chênh 2% |
| `judge_accuracy` | 0.6667 | 0.5556 | 0.6667 | -16.67% | 100% | Phục hồi hoàn toàn |
| `mean_judge_score` | 3.5000 | 3.2222 | 3.5000 | -7.94% | 100% | Phục hồi hoàn toàn |
| Quality checks | 6/6 | 3/6 | 6/6 | -3 checks | 100% | summary, unique, freshness fail |
| Freshness status | FRESH | STALE | FRESH | Stale | 100% | 5 stale rows do inject date 2020 |

Kết luận nhân quả:

1. **Corruption -> Quality signal -> Metric giảm**: Blank summary + drop latest records -> quality checks fail (summary_not_empty, uniqueness) -> retrieval_hit_rate giảm 16.7% (3/18 câu hỏi tìm sai document) -> judge_score giảm từ 3.5 xuống 3.22.

2. **Repair -> Quality phục hồi -> Metric phục hồi**: Re-clean từ raw source -> quality 6/6 PASSED, freshness FRESH -> retrieval_hit_rate phục hồi 1.0, judge_score phục hồi 3.5. Token F1 chênh 2% do LLM nondeterministic, không phải do data.

## 11. Vấn đề tích hợp quan trọng

- **Triệu chứng**: LLM judge fallback heuristic 18/18 câu hỏi — tất cả điểm đều từ fallback, không có real LLM evaluation.
- **Nguyên nhân**: `with_structured_output()` trong LangChain tạo request mới không kế thừa `max_tokens=1024`, gửi mặc định 65535 tokens -> OpenRouter trả 402 (insufficient credits). Exception bị catch silently trong `except Exception` -> fallback.
- **Cách xử lý**: Thay `with_structured_output()` bằng gọi LLM trực tiếp với `max_tokens=512`, parse JSON response thủ công thành `JudgeVerdict`.
- **Cách xác minh**: Chạy lại evaluation -> 18/18 câu đều dùng real LLM judge (0 fallback).

## 12. Giới hạn và hướng cải thiện

| Giới hạn hiện tại | Ảnh hưởng | Hướng cải thiện có thể kiểm chứng |
|-------------------|-----------|-----------------------------------|
| `published` date không nằm trong `text_for_embedding` | 6/6 date questions có token_f1 = 0.0 | Thêm `"Published: {date}"` vào text_for_embedding -> date F1 tăng |
| `categories` rỗng 100% từ Crossref | Không tạo được câu hỏi categories | Bổ sung query khác hoặc dùng API khác có subject |
| LLM nondeterministic | Token F1 repaired chênh 2% so với baseline | Set temperature=0 và seed cố định (nếu model hỗ trợ) |
| RAGAS chưa chạy | Thiếu metrics faithfulness, context_precision | Bật `RUN_RAGAS=1` với đủ API credits |

## 13. Checklist trước khi nộp

- [x] Thông tin nhóm và repository chính xác.
- [x] Phân công khớp với module, artifact và kết quả thực tế.
- [x] Lệnh tái hiện đã được chạy lại trên phiên bản dùng để nộp.
- [x] Baseline, corrupted và repaired dùng cùng evaluation set.
- [x] Bảng metrics khớp với các file trong `data/results/`.
- [x] Quality/freshness conclusions khớp với `data/quality/`.
- [x] Các đường dẫn báo cáo và artifact truy cập được.
- [x] Mỗi thành viên đã hoàn thành báo cáo vai trò riêng.
- [x] Không có `.env`, API key, token hoặc secret trong source, report, log hay ảnh.
