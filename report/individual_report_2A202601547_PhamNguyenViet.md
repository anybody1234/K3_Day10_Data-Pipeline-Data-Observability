# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin | Nội dung |
|-----------|----------|
| Họ và tên | Phạm Nguyên Việt |
| MSSV | 2A202601547 |
| Khóa/Lớp | K3 |
| Tên nhóm | Nhóm 4 |
| Vai trò chính | Vai trò 3 — RAG & agent owner |
| Repository | https://github.com/VinUni-AI20k/K3_Day10_Data-Pipeline-Data-Observability |
| Ngày hoàn thành | 2026-08-06 |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
|--------------------|-------------------|---------------|-----------------|------------|
| Embedding engine | `src/retrieval/embeddings.py` -> `MiniLMEmbeddings` | Embedding model name | Embedding functions cho ChromaDB | Hoàn thành |
| Vector index | `src/retrieval/index.py` -> `LocalEmbeddingIndex` | Clean DataFrame + Settings | ChromaDB collection + embedding manifest | Hoàn thành |
| QA retrieval | `src/retrieval/qa.py` -> `answer_question()` | Question + index | AnswerResult (answer, doc_ids, contexts) | Hoàn thành |
| LLM builder | `src/retrieval/llm.py` -> `build_llm()` | Settings + temperature | LangChain LLM object | Hoàn thành |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả |
|-----------|------------------------------|---------|
| Fix OpenRouter max_tokens | Vai trò 4 (metrics.py) | Thêm `max_tokens=1024` vào OpenRouter provider |
| Demo semantic search | Vai trò 1 (Pipeline) | Xác nhận retrieval hoạt động trước evaluation |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
|------------------------|----------------------------|------------------|---------------|
| Build MiniLM embedding engine | `embeddings.py` | MiniLMEmbeddings class wrapping sentence-transformers | Import và gọi `embed_documents()` |
| Build ChromaDB index từ clean data | `index.py` -> `build()` | `data/embeddings/papers_embeddings.json`, ChromaDB collections | `LocalEmbeddingIndex.load(s)` thành công |
| Implement semantic search + exact lookup | `index.py` -> `search()`, `lookup()` | SearchResult với paper_id, title, score, content, metadata | Test query trả kết quả có nguồn |
| Implement QA answer extraction | `qa.py` -> `answer_question()` | AnswerResult với retrieved contexts | Kiểm tra answer dựa trên retrieved docs |
| Build multi-provider LLM | `llm.py` -> `build_llm()` | LLM object hỗ trợ OpenRouter, OpenAI, Gemini, Anthropic, Ollama | Gọi `llm.invoke()` không lỗi |

Artifact chính: **3 ChromaDB collections** (`papers-baseline`, `papers-corrupted`, `papers-repaired`) với 24 documents mỗi collection, tách biệt để so sánh.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Vai trò 3 chịu trách nhiệm xây dựng **hệ thống retrieval** cho RAG pipeline: từ embedding model, vector store, đến search/lookup interface mà evaluation module gọi.

### Cách triển khai

**Embedding (`embeddings.py`):**
- Wrap `sentence-transformers/all-MiniLM-L6-v2` thành `MiniLMEmbeddings` class
- Cung cấp `embed_documents()` và `embed_query()` cho ChromaDB

**Vector index (`index.py`):**
- `build()`: nhận DataFrame, encode `text_for_embedding` thành vector 384d, lưu ChromaDB collection với cosine similarity
- `load()`: đọc manifest JSON, kết nối lại ChromaDB PersistentClient
- `search()`: semantic search top-K bằng query embedding
- `lookup()`: exact title match bằng dictionary lookup
- Collection naming: `papers-baseline`, `papers-corrupted`, `papers-repaired` (derive từ output path)

**QA retrieval (`qa.py`):**
- `answer_question()`: kết hợp exact title match (từ question quotes) + semantic search
- Exact match được ưu tiên (đặt đầu kết quả, dedupe)
- `_extract_answer()`: rule-based extraction từ metadata (dùng cho fallback)

**LLM builder (`llm.py`):**
- Multi-provider: OpenRouter, OpenAI, Gemini, Anthropic, Ollama, Custom
- OpenRouter cần `max_tokens=1024` explicit (free-tier giới hạn)

### Input, output và contract

| Thành phần | Mô tả |
|-----------|-------|
| Input | Clean DataFrame (từ cleaning), Settings (từ config) |
| Output | ChromaDB collections, embedding manifest JSON, AnswerResult |
| Module phụ thuộc | `src/core/config.py`, `src/core/utils.py`, sentence-transformers, chromadb |
| Module sử dụng output | `src/evaluation/metrics.py` (evaluate_pipeline gọi answer_question + build_llm) |
| Điều kiện lỗi | ChromaDB persist_path sai (absolute path máy khác), OpenRouter 402 |

### Cách xác minh

```bash
# Test index build + search
python -c "
import sys; sys.path.insert(0,'src')
from core.config import load_settings
from retrieval.index import LocalEmbeddingIndex
s = load_settings()
idx = LocalEmbeddingIndex.load(s)
results = idx.search('retrieval augmented generation', top_k=3)
for r in results: print(r.paper_id, r.score)
"
```

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Khi answer_question() nhận câu hỏi chứa title trong dấu nháy đơn (ví dụ "What is the main finding of 'SafeRAG...'?"), cần quyết định dùng semantic search hay exact title match.
- **Các phương án:**
  1. Chỉ semantic search: đơn giản nhưng có thể miss khi title dài/đa ngôn ngữ.
  2. Kết hợp exact title match + semantic search: chính xác hơn nhưng phức tạp hơn.
- **Phương án đã chọn:** Kết hợp cả hai (phương án 2). Regex extract title từ quotes, lookup exact match, đặt lên đầu kết quả, dedupe, rồi fill phần còn lại bằng semantic search.
- **Lý do:** Test set chứa câu hỏi trích dẫn exact title. Semantic search có thể trả về paper khác có nội dung tương tự. Exact match đảm bảo retrieval_hit_rate cao.
- **Bằng chứng:** `retrieval_hit_rate = 1.0` cho cả 18 câu hỏi.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng:** `chromadb.errors.InternalError: failed to create whole tree` khi `LocalEmbeddingIndex.load()`.
- **Nguyên nhân gốc:** `papers_embeddings.json` chứa `persist_path: D:\VIET\VIN\...` (đường dẫn absolute của máy teammate). Khi load trên máy khác, ChromaDB không tìm được thư mục.
- **Cách xử lý:** Rebuild index từ local clean data bằng `LocalEmbeddingIndex.build(df, settings)`. File manifest được ghi lại với path local.
- **Cách xác minh:** `LocalEmbeddingIndex.load(s)` thành công, `search()` trả kết quả.
- **Điều học được:** Không commit absolute path. Nên dùng relative path hoặc derive từ Settings.

## 7. Hiểu biết về luồng end-to-end

**1. Dữ liệu đi từ Crossref đến vector index như thế nào?**

Crossref API -> fetch + parse thành PaperRecord -> clean DataFrame (normalize, dedupe, tạo `text_for_embedding`) -> `LocalEmbeddingIndex.build()`: encode `text_for_embedding` qua MiniLM-L6-v2 -> vector 384 chiều -> lưu ChromaDB collection `papers-baseline` với cosine similarity + metadata (paper_id, title, authors, published, summary).

**2. Evaluation set và ground-truth document IDs dùng để đo retrieval/answer quality ra sao?**

Mỗi câu hỏi có `ground_truth_doc_ids` (DOI). Khi evaluate: retrieval top-K docs -> kiểm tra DOI gốc có trong kết quả không (hit_rate). LLM sinh answer từ contexts -> so token F1 với ground_truth.

**3. Quality checks khác freshness monitoring ở điểm nào?**

Quality checks = tính đúng đắn cấu trúc (không null, không trùng). Freshness = tính kịp thời (age_days <= 180). Hai dimension khác nhau, bắt được loại corruption khác nhau.

**4. Vì sao phải dùng cùng test set cho baseline, corrupted và repaired?**

Controlled experiment: chỉ thay đổi data, giữ nguyên test set -> delta metrics chỉ do data quality.

**5. Repair được xem là thành công dựa trên artifact và metric nào?**

Rebuild index từ repaired clean data -> `repaired_metrics.json` gần baseline, quality 6/6, freshness FRESH. Collection `papers-repaired` có đúng 24 documents.

## 8. Phân tích kết quả

### Metrics chính

| Metric/signal | Baseline | Corrupted | Repaired | Nhận xét của cá nhân |
|---------------|----------|-----------|----------|---------------------|
| `retrieval_hit_rate` | 1.0000 | 0.8333 | 1.0000 | Exact title match cứu nhiều câu, nhưng blank summary vẫn gây miss |
| `mean_token_f1` | 0.1809 | 0.1440 | 0.1773 | Context kém -> LLM answer kém |
| `judge_accuracy` | 0.6667 | 0.5556 | 0.6667 | Phục hồi hoàn toàn |
| `mean_judge_score` | 3.5000 | 3.2222 | 3.5000 | Phục hồi hoàn toàn |
| Quality checks | 6/6 | 3/6 | 6/6 | Index quality phụ thuộc clean data quality |
| Freshness status | FRESH | STALE | FRESH | Không ảnh hưởng retrieval trực tiếp |

### Kết luận từ số liệu

Embedding quality phụ thuộc hoàn toàn vào `text_for_embedding`. Blank summary -> embedding gần như zero-information -> semantic search trả về sai document. Exact title match giúp mitigrate một phần nhưng không đủ khi title cũng bị truncate.

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất

1. **Embedding schema thiết kế:** `text_for_embedding` quyết định retrieval quality. Thiếu published date -> date questions fail. Cần cân nhắc query types khi thiết kế.

2. **Collection isolation:** 3 collections riêng cho 3 trạng thái là thiết kế đúng. Nếu ghi đè, mất khả năng so sánh.

3. **Multi-provider LLM:** Cần set `max_tokens` explicit cho mỗi provider. Mặc định của LangChain (65535) gây lỗi 402 trên free-tier.

### Nếu có thêm thời gian

Thử hybrid retrieval (dense + sparse/BM25) thay vì chỉ dense embedding. Sparse retrieval có thể bắt exact keyword match tốt hơn cho date/author queries.

## 10. Cam kết của thành viên

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi "đã chạy thành công" cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Phạm Nguyên Việt
**Ngày xác nhận:** 2026-08-06
