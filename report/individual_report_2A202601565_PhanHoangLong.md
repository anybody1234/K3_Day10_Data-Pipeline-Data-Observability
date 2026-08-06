# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin | Nội dung |
|-----------|----------|
| Họ và tên | Phan Hoàng Long |
| MSSV | 2A202601565 |
| Khóa/Lớp | K3 |
| Tên nhóm | Nhóm 4 |
| Vai trò chính | Vai trò 2 — Nền tảng dữ liệu & recovery (Data foundation & recovery) |
| Repository | https://github.com/VinUni-AI20k/K3_Day10_Data-Pipeline-Data-Observability |
| Ngày hoàn thành | 2026-08-06 |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
|--------------------|-------------------|---------------|-----------------|------------|
| Raw ingestion | `src/ingestion/crossref.py` -> `fetch_source_records()`, `parse_crossref_payload()`, `load_raw_records()` | Crossref API + Settings | `data/raw/crossref_response.json`, `data/raw/crossref_records.json` | Hoàn thành |
| Cleaning & data modeling | `src/ingestion/cleaning.py` -> `build_clean_dataframe()` | Raw records + run_date | `data/clean/papers_clean.csv`, `data/clean/papers_clean.json` | Hoàn thành |
| Corruption simulation | `src/ingestion/corruption.py` -> `corrupt_clean_dataframe()` | Clean DataFrame | `papers_clean_corrupted.csv`, `corruption_log.json` | Hoàn thành |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả |
|-----------|------------------------------|---------|
| Xác minh raw -> clean lineage | Vai trò 4 (Evaluation) | Đảm bảo paper_id stable xuyên suốt pipeline |
| Cung cấp source evidence cho repair | Vai trò 1 (Pipeline) | Raw records dùng làm điểm khôi phục |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
|------------------------|----------------------------|------------------|---------------|
| Fetch Crossref API với retry/backoff | `crossref.py` -> `fetch_source_records()` | 24 records, raw JSON lưu tại `data/raw/` | `ls data/raw/crossref_response.json` |
| Parse Crossref payload thành PaperRecord | `crossref.py` -> `parse_crossref_payload()` | 24 PaperRecord với DOI = paper_id | Kiểm tra `data/raw/crossref_records.json` |
| Clean data: normalize, dedupe, tạo text_for_embedding | `cleaning.py` -> `build_clean_dataframe()` | 24 rows clean, 14 cột, 0 dropped | `data/clean/papers_clean.csv` |
| Áp dụng 6 loại corruption | `corruption.py` -> `corrupt_clean_dataframe()` | Corrupted dataset + corruption_log.json | `data/results/corruption_log.json` |

Artifact chính: **Clean dataset** với `text_for_embedding` đúng format và `paper_id` (DOI) stable xuyên suốt pipeline.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Vai trò 2 chịu trách nhiệm **thu thập, làm sạch và mô hình hóa dữ liệu** từ Crossref API, tạo ra clean dataset phục vụ embedding và evaluation. Đồng thời implement corruption scenarios để kiểm chứng tác động của data xấu lên RAG.

### Cách triển khai

**Ingestion (`crossref.py`):**
1. Gọi Crossref API với query `agentic retrieval augmented generation large language model`
2. Retry 3 lần với backoff 2-4-8s cho HTTP 429/503 và Timeout
3. Lưu raw JSON response trước khi parse (traceability)
4. Parse: DOI -> paper_id, title[0] -> title (strip HTML), abstract -> summary (strip HTML), author -> authors, published/deposited -> dates
5. Skip records thiếu DOI, title, hoặc abstract

**Cleaning (`cleaning.py`):**
1. Normalize whitespace (xóa `\n`, `\t`, khoảng trắng thừa)
2. Filter rows có title/summary rỗng
3. Deduplicate theo paper_id (giữ bản đầu tiên)
4. Tạo `authors_joined` = join list tác giả bằng dấu phẩy
5. Tạo `text_for_embedding` = `"{title}. {summary} Authors: {authors_joined}"`
6. Tính `age_days` = (run_date - published_date).days
7. Sort theo published giảm dần

**Corruption (`corruption.py`):**
6 loại corruption có kiểm soát (seed=42, mỗi loại 4 records):
1. Drop latest records: xóa 4 bài mới nhất
2. Blank summary: xóa trắng abstract
3. Inject noise: chèn text nhiễu vào summary
4. Truncate title: cắt ngắn tiêu đề
5. Stale dates: đổi published thành 2020-01-01
6. Duplicate rows: nhân đôi 4 records

### Input, output và contract

| Thành phần | Mô tả |
|-----------|-------|
| Input | Crossref API response (JSON) |
| Output | Raw records, clean CSV/JSON, corrupted CSV, corruption_log.json |
| Module phụ thuộc | `src/core/config.py` (Settings, Paths), `src/core/utils.py` (normalize_whitespace, compact_join) |
| Module sử dụng output | `src/retrieval/index.py` (build embedding), `src/evaluation/testset.py` (tạo test set) |
| Điều kiện lỗi | API timeout (60s), HTML tags trong abstract, timezone mismatch (tz-aware vs tz-naive) |

### Cách xác minh

```bash
# Kiểm tra raw data
python -c "import json; data=json.load(open('data/raw/crossref_records.json')); print(len(data), 'records')"

# Kiểm tra clean data
python -c "import pandas as pd; df=pd.read_csv('data/clean/papers_clean.csv'); print(df.shape, df['paper_id'].duplicated().sum(), 'duplicates')"

# Kiểm tra corruption log
python -c "import json; log=json.load(open('data/results/corruption_log.json')); print(list(log['operations'].keys()))"
```

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Crossref API trả về `abstract` chứa HTML tags (`<jats:p>`, `<jats:italic>`, `<jats:sub>`). Cần quyết định xử lý khi nào: lúc parse raw hay lúc clean.
- **Các phương án:**
  1. Strip HTML lúc parse (`parse_crossref_payload`): raw records đã sạch, nhưng mất traceability.
  2. Strip HTML lúc clean (`build_clean_dataframe`): raw giữ nguyên gốc, clean mới xử lý.
- **Phương án đã chọn:** Strip HTML lúc parse (phương án 1), vì PaperRecord contract yêu cầu summary là plain text.
- **Lý do:** Các module downstream (embedding, evaluation) đều mong đợi plain text. Nếu để HTML trong raw records, mọi consumer phải tự strip -> dễ quên -> embedding chứa HTML tags.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng:** `TypeError: can't subtract offset-naive and offset-aware datetimes` khi tính `age_days` trong `build_clean_dataframe()`.
- **Nguyên nhân gốc:** `now_utc()` trả về datetime tz-aware (UTC), nhưng `pd.to_datetime(published)` trả về tz-naive. Phép trừ 2 kiểu datetime khác nhau gây TypeError.
- **Cách xử lý:** Thêm `run_date.replace(tzinfo=None)` để chuyển run_date thành tz-naive trước khi trừ.
- **Cách xác minh:** Chạy lại `build_clean_dataframe()` -> `age_days` tính đúng, không lỗi.

## 7. Hiểu biết về luồng end-to-end

**1. Dữ liệu đi từ Crossref đến vector index như thế nào?**

Crossref API -> `fetch_source_records()` với retry/backoff -> `parse_crossref_payload()` parse thành PaperRecord (DOI = paper_id, strip HTML) -> `build_clean_dataframe()` normalize, dedupe, tạo `text_for_embedding` -> `LocalEmbeddingIndex.build()` encode MiniLM-L6-v2 -> ChromaDB collection.

**2. Evaluation set và ground-truth document IDs dùng để đo retrieval/answer quality ra sao?**

Test set 18 câu hỏi, mỗi câu có `ground_truth_doc_ids` (DOI từ clean data). `retrieval_hit_rate` = tỷ lệ câu mà top-K chứa đúng DOI gốc. `token_f1` = token overlap giữa LLM answer và ground_truth.

**3. Quality checks khác freshness monitoring ở điểm nào?**

Quality checks đo tính đúng đắn cấu trúc (null, empty, duplicate). Freshness đo tính kịp thời (age_days vs threshold 180 ngày). Corruption "stale dates" chỉ bị freshness bắt, không bị quality checks bắt.

**4. Vì sao phải dùng cùng test set cho baseline, corrupted và repaired?**

Cùng test set -> cùng câu hỏi -> thay đổi metrics chỉ do data, không do câu hỏi khác. Đây là nguyên tắc controlled experiment.

**5. Repair được xem là thành công dựa trên artifact và metric nào?**

Repair thành công khi repaired_metrics gần baseline, quality 6/6 PASSED, freshness FRESH. Raw source không bị mutation nên re-clean luôn khôi phục được.

## 8. Phân tích kết quả

### Metrics chính

| Metric/signal | Baseline | Corrupted | Repaired | Nhận xét của cá nhân |
|---------------|----------|-----------|----------|---------------------|
| `retrieval_hit_rate` | 1.0000 | 0.8333 | 1.0000 | Drop + blank gây 3 retrieval miss |
| `mean_token_f1` | 0.1809 | 0.1440 | 0.1773 | Noise và blank làm context kém |
| `judge_accuracy` | 0.6667 | 0.5556 | 0.6667 | Phục hồi hoàn toàn |
| `mean_judge_score` | 3.5000 | 3.2222 | 3.5000 | Phục hồi hoàn toàn |
| Quality checks | 6/6 | 3/6 | 6/6 | 3 fails: summary, unique, freshness |
| Freshness status | FRESH | STALE | FRESH | 5 stale rows do date 2020 |

### Kết luận từ số liệu

Blank summary là corruption ảnh hưởng nặng nhất: `text_for_embedding` gần như rỗng -> embedding vô nghĩa -> retrieval miss. Drop latest records cũng nghiêm trọng vì xóa mất document mà test set đang hỏi. Repair từ raw source khôi phục 100% vì raw không bị mutation.

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất

1. **Data lineage:** Lưu raw response trước khi parse là bắt buộc. Khi cần repair, raw source là điểm khôi phục duy nhất đáng tin cậy.

2. **text_for_embedding quyết định retrieval quality:** Thiết kế field này cần cân nhắc kỹ query types. Thiếu published date trong embedding -> 6/6 date questions fail.

3. **Corruption có kiểm soát:** Log rõ paper_id, loại corruption, before/after count giúp truy vết chính xác tác động.

### Nếu có thêm thời gian

Thêm `published` date vào `text_for_embedding` (format: `"Published: 2026-08-01"`) để LLM trả lời được date questions. Hiện tại 6 date questions đều fail (F1 = 0.0).

## 10. Cam kết của thành viên

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi "đã chạy thành công" cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Phan Hoàng Long
**Ngày xác nhận:** 2026-08-06
