# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin | Nội dung |
|-----------|----------|
| Họ và tên | Lục Minh Đức |
| MSSV | 2A202601918 |
| Khóa/Lớp | K3 |
| Tên nhóm | Nhóm 4 |
| Vai trò chính | Vai trò 1 — Điều phối pipeline (Pipeline integrator) |
| Repository | https://github.com/VinUni-AI20k/K3_Day10_Data-Pipeline-Data-Observability |
| Ngày hoàn thành | 2026-08-06 |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
|--------------------|-------------------|---------------|-----------------|------------|
| Cấu hình pipeline | `src/core/config.py` -> `Settings`, `Paths`, `load_settings()` | `.env`, environment variables | Settings object cho toàn bộ pipeline | Hoàn thành |
| Baseline orchestration | `src/pipelines/phase1.py` -> `main()` | Raw records + Settings | Toàn bộ baseline artifacts | Hoàn thành |
| Corruption flow | `src/pipelines/corruption_flow.py` -> `main()` | Baseline artifacts + Settings | Corrupted + Repaired artifacts + comparison report | Hoàn thành |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả |
|-----------|------------------------------|---------|
| Chốt contract raw/clean schema | Toàn nhóm | Thống nhất PaperRecord, paper_id = DOI, paths artifact |
| Kiểm tra dependencies và môi trường | Toàn nhóm | Xác nhận Python 3.11+, uv sync hoạt động |
| Debug integration issues | `metrics.py`, `llm.py` | Fix max_tokens cho OpenRouter |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
|------------------------|----------------------------|------------------|---------------|
| Thiết lập cấu hình Settings/Paths | `config.py` | Settings object với tất cả paths, providers, thresholds | `load_settings()` không lỗi |
| Orchestrate phase1 pipeline | `phase1.py` | Baseline artifacts đầy đủ | `python script/run_phase1.py` exit code 0, artifacts tồn tại |
| Orchestrate corruption flow | `corruption_flow.py` | 3 bộ metrics + comparison report | `python script/run_corruption_flow.py`, kiểm tra `data/reports/corruption_report.md` |
| Chạy end-to-end và demo | Toàn pipeline | Pipeline chạy từ đầu đến cuối không lỗi | Chạy lại trên máy sạch |

Artifact chính: **Pipeline end-to-end chạy được** — từ Crossref API đến comparison report, tái hiện bằng 2 lệnh.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Vai trò 1 chịu trách nhiệm **điều phối và tích hợp** toàn bộ pipeline: đảm bảo các module (ingestion, cleaning, embedding, evaluation, observability) kết nối đúng contract, chạy đúng thứ tự, và tạo ra artifacts nhất quán.

### Cách triển khai

**Phase 1 pipeline (`phase1.py`):**
1. Fetch raw records từ Crossref API
2. Clean data thành DataFrame
3. Build embedding index (ChromaDB)
4. Generate test set từ clean data
5. Evaluate baseline (retrieval + LLM RAG + LLM judge)
6. Run quality checks và freshness
7. Generate phase1 report

**Corruption flow (`corruption_flow.py`):**
1. Load baseline clean data
2. Apply 6 loại corruption (seed=42)
3. Rebuild embedding index cho corrupted data (collection riêng)
4. Evaluate corrupted với cùng test set
5. Repair từ raw source -> re-clean -> rebuild index -> re-evaluate
6. Generate comparison report

### Input, output và contract

| Thành phần | Mô tả |
|-----------|-------|
| Input | `.env` (LLM config), raw records từ Crossref |
| Output | Toàn bộ artifacts trong `data/` |
| Module phụ thuộc | Tất cả modules trong `src/` |
| Điều kiện lỗi | API timeout, thiếu credentials, path conflict giữa 3 trạng thái |

### Cách xác minh

```bash
python script/run_phase1.py
python script/run_corruption_flow.py
ls data/results/*.json data/reports/*.md data/quality/*.json
```

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Cần quyết định cách tổ chức 3 trạng thái (baseline/corrupted/repaired) trong cùng ChromaDB instance — dùng chung collection hay tách riêng.
- **Các phương án:**
  1. Ghi đè cùng collection: đơn giản nhưng mất baseline, không so sánh được.
  2. Tách 3 collection riêng (`papers-baseline`, `papers-corrupted`, `papers-repaired`): phức tạp hơn nhưng giữ nguyên baseline.
- **Phương án đã chọn:** Tách 3 collection riêng (phương án 2).
- **Lý do:** Checkpoint yêu cầu so sánh 3 trạng thái trên cùng test set. Ghi đè sẽ mất baseline và không thể tái hiện.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng:** `papers_embeddings.json` chứa `persist_path: D:\VIET\VIN\...` (đường dẫn máy khác) -> ChromaDB crash "failed to create whole tree".
- **Nguyên nhân gốc:** Teammate commit file embeddings với absolute path của máy họ. Khi load trên máy khác, ChromaDB không tìm được thư mục.
- **Cách xử lý:** Rebuild index từ local clean data bằng `LocalEmbeddingIndex.build()`, ghi đè `papers_embeddings.json` với path local.
- **Cách xác minh:** Load index thành công, semantic search trả về kết quả.

## 7. Hiểu biết về luồng end-to-end

**1. Dữ liệu đi từ Crossref đến vector index như thế nào?**

Crossref API -> `fetch_source_records()` lấy raw JSON -> `parse_crossref_payload()` parse thành `PaperRecord` (DOI = paper_id) -> `build_clean_dataframe()` normalize, dedupe, tạo `text_for_embedding` = title + summary + authors -> `LocalEmbeddingIndex.build()` encode qua MiniLM-L6-v2 thành vector 384d -> lưu ChromaDB collection.

**2. Evaluation set và ground-truth document IDs dùng để đo retrieval/answer quality ra sao?**

Test set chứa 18 câu hỏi, mỗi câu có `ground_truth` và `ground_truth_doc_ids` (paper DOI). Khi evaluate: `retrieval_hit_rate` = tỷ lệ câu mà top-K docs chứa đúng ground_truth_doc_ids; `token_f1` = token-level F1 giữa LLM answer và ground_truth; `judge` = LLM chấm 1-5.

**3. Quality checks khác freshness monitoring ở điểm nào?**

Quality checks kiểm tra tính đúng đắn cấu trúc (completeness, uniqueness). Freshness monitoring kiểm tra tính kịp thời (timeliness): bao nhiêu records có `age_days` vượt ngưỡng 180 ngày.

**4. Vì sao phải dùng cùng test set cho baseline, corrupted và repaired?**

Để so sánh công bằng. Nếu dùng test set khác, không thể kết luận thay đổi metrics là do data corruption hay do câu hỏi khác.

**5. Repair được xem là thành công dựa trên artifact và metric nào?**

Repair thành công khi: repaired_metrics gần bằng baseline; quality 6/6 PASSED; freshness FRESH. Thực tế: hit_rate phục hồi 1.0, judge_score phục hồi 3.5, quality 6/6.

## 8. Phân tích kết quả

### Metrics chính

| Metric/signal | Baseline | Corrupted | Repaired | Nhận xét của cá nhân |
|---------------|----------|-----------|----------|---------------------|
| `retrieval_hit_rate` | 1.0000 | 0.8333 | 1.0000 | Corruption làm 3/18 câu tìm sai doc; repair phục hồi 100% |
| `mean_token_f1` | 0.1809 | 0.1440 | 0.1773 | Giảm 20% khi corrupt, phục hồi 98% khi repair |
| `judge_accuracy` | 0.6667 | 0.5556 | 0.6667 | Phục hồi hoàn toàn |
| `mean_judge_score` | 3.5000 | 3.2222 | 3.5000 | Phục hồi hoàn toàn |
| Quality checks | 6/6 | 3/6 | 6/6 | 3 checks fail: summary_empty, uniqueness, freshness |
| Freshness status | FRESH | STALE | FRESH | 5 stale rows do inject date 2020-01-01 |

### Kết luận từ số liệu

Corruption ảnh hưởng rõ nhất đến retrieval: drop + blank summary gây miss 3 câu hỏi. Repair từ raw source phục hồi gần 100% metrics, chứng minh tầm quan trọng của việc giữ nguyên dữ liệu nguồn.

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất

1. **Pipeline orchestration:** Thứ tự chạy các module rất quan trọng — phải có clean data trước khi build index, phải có index trước khi evaluate.

2. **Path management:** Absolute path trong artifacts gây lỗi khi chạy trên máy khác. Nên dùng relative path hoặc rebuild từ config.

3. **Contract giữa modules:** Khi 4 người làm song song, contract (schema, paths, collection names) phải chốt trước. Thay đổi contract giữa chừng gây cascade failures.

### Nếu có thêm thời gian

Thêm CI/CD pipeline tự động chạy baseline + corruption flow khi push code, đảm bảo pipeline luôn tái hiện được.

## 10. Cam kết của thành viên

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi "đã chạy thành công" cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Lục Minh Đức
**Ngày xác nhận:** 2026-08-06
