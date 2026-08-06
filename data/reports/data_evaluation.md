# Đánh giá dữ liệu trước và sau khi Clean

## 1. Dữ liệu thô (Raw Data)

### 1.1 Nguồn dữ liệu

| Thông tin | Chi tiết |
|-----------|----------|
| API | Crossref REST API (`https://api.crossref.org/works`) |
| Query | `agentic retrieval augmented generation large language model` |
| Filter | `from-pub-date:2026-02-07`, `has-abstract:true` |
| Tổng kết quả trên API | 100,916 |
| Số record đã lấy | 24 (giới hạn bởi `max_results=24`) |
| Cơ chế retry | 3 lần, backoff 2-4-8s, xử lý 429/503/Timeout |
| Timeout | 60s |

### 1.2 Schema dữ liệu thô (11 trường)

| Trường | Nguồn Crossref | Kiểu | Mô tả |
|--------|---------------|------|--------|
| `paper_id` | `DOI` | string | Mã định danh DOI |
| `title` | `title[0]` | string | Tiêu đề bài báo |
| `summary` | `abstract` | string | Tóm tắt (abstract) |
| `authors` | `author[].given + family` | list[string] | Danh sách tác giả |
| `categories` | `subject` | list[string] | Danh mục chủ đề |
| `primary_category` | `subject[0]` | string | Danh mục chính |
| `published` | `published.date-parts[0]` | string | Ngày xuất bản (YYYY-MM-DD) |
| `updated` | `deposited.date-parts[0]` | string | Ngày cập nhật metadata |
| `abs_url` | `URL` | string | URL trang bài báo |
| `pdf_url` | `link[0].URL` | string | URL file PDF |
| `comment` | *(không có)* | string | Ghi chú (luôn rỗng) |

### 1.3 Missing Values (Raw)

| Trường | Số record thiếu | Tỷ lệ |
|--------|----------------|--------|
| `paper_id` | 0 | 0% |
| `title` | 0 | 0% |
| `summary` | 0 | 0% |
| `authors` | 0 | 0% |
| `categories` | **24** | **100%** |
| `published` | 0 | 0% |
| `updated` | 0 | 0% |
| `abs_url` | 0 | 0% |
| `pdf_url` | **8** | **33%** |

- **Categories rỗng 100%**: Crossref API không trả trường `subject` cho query này.
- **PDF URL thiếu 33%**: Một số nhà xuất bản không cung cấp link PDF qua API.

### 1.4 File lưu trữ

| File | Đường dẫn |
|------|-----------|
| Raw API response | `data/raw/crossref_response.json` |
| Parsed records | `data/raw/crossref_records.json` |

---

## 2. Dữ liệu sạch (Clean Data)

### 2.1 Các bước xử lý

| Bước | Xử lý | Mô tả |
|------|--------|--------|
| 1 | Strip HTML tags | Xóa `<jats:p>`, `<jats:italic>`, v.v. trong abstract |
| 2 | Normalize whitespace | Chuẩn hóa khoảng trắng thừa, xuống dòng, tab |
| 3 | Filter rows xấu | Loại bỏ rows có title hoặc summary rỗng |
| 4 | Drop duplicates | Xóa records trùng `paper_id`, giữ bản đầu tiên |
| 5 | Tạo `authors_joined` | Join list tác giả thành chuỗi phân cách bằng dấu phẩy |
| 6 | Tạo `categories_joined` | Join list danh mục thành chuỗi |
| 7 | Tính `summary_chars` | Đếm số ký tự của summary |
| 8 | Tính `age_days` | Số ngày từ ngày xuất bản đến thời điểm chạy pipeline |
| 9 | Tạo `text_for_embedding` | `"{title}. {summary} Authors: {authors_joined}"` |
| 10 | Sort | Sắp xếp theo `published` giảm dần |

### 2.2 Schema dữ liệu sạch (14 cột)

| Cột | Kiểu | Null | Mô tả |
|-----|------|------|--------|
| `paper_id` | string | 0 | DOI — khóa chính, unique |
| `title` | string | 0 | Tiêu đề đã chuẩn hóa |
| `summary` | string | 0 | Abstract đã strip HTML |
| `primary_category` | float | 24 | Rỗng do API không trả |
| `published` | string | 0 | Ngày xuất bản (YYYY-MM-DD) |
| `updated` | string | 0 | Ngày cập nhật metadata |
| `abs_url` | string | 0 | URL trang bài báo |
| `pdf_url` | string | 8 | URL PDF (8 records thiếu) |
| `comment` | float | 24 | Luôn rỗng |
| `authors_joined` | string | 0 | Tác giả đã join |
| `categories_joined` | float | 24 | Rỗng do API |
| `summary_chars` | int | 0 | Số ký tự summary |
| `text_for_embedding` | string | 0 | Văn bản kết hợp cho embedding |
| `age_days` | int | 0 | Số ngày kể từ ngày xuất bản |

### 2.3 Thống kê mô tả

| Chỉ số | `age_days` | `summary_chars` |
|--------|-----------|----------------|
| Min | 5 | 834 |
| Max | 175 | 2,610 |
| Mean | 78.2 | 1,728.0 |
| Median | 66.0 | 1,661.0 |

### 2.4 File lưu trữ

| File | Đường dẫn |
|------|-----------|
| CSV | `data/clean/papers_clean.csv` |
| JSON | `data/clean/papers_clean.json` |

---

## 3. So sánh trước và sau khi Clean

| Tiêu chí | Raw Data | Clean Data |
|----------|----------|------------|
| Số records | 24 | 24 |
| Số trường/cột | 11 | 14 |
| Records bị loại | -- | 0 |
| Duplicates bị xóa | -- | 0 |
| HTML trong text | Co (`<jats:p>`, ...) | Đã xóa |
| Whitespace thừa | Co | Đã chuẩn hóa |
| Cột mới thêm | -- | `authors_joined`, `categories_joined`, `summary_chars`, `text_for_embedding`, `age_days` |
| Cột bị xóa | -- | `authors` (list), `categories` (list) -> thay bằng `_joined` |
| Sắp xếp | Theo thứ tự API | Theo `published` giảm dần |

---

## 4. Đặc điểm đáng chú ý

1. **Categories rỗng 100%**: Crossref API không trả trường `subject` cho query này. Không ảnh hưởng embedding (vì `text_for_embedding` không dùng categories) nhưng ảnh hưởng đến việc tạo câu hỏi "categories" trong evaluation.

2. **PDF URL thiếu 33%**: 8/24 bài không có link PDF. Không ảnh hưởng pipeline vì embedding chỉ dùng abstract.

3. **Dữ liệu đa ngôn ngữ**: Một số bài có title/summary bằng tiếng Nga, tiếng Trung. MiniLM hỗ trợ đa ngôn ngữ nhưng chất lượng retrieval có thể thấp hơn so với bài tiếng Anh.

4. **Không mất dữ liệu khi clean**: Tất cả 24 records đều hợp lệ (có title và summary), không record nào bị loại.

5. **Freshness**: Tất cả 24 bài đều trong ngưỡng 180 ngày (max age = 175 ngày). Khoảng thời gian: 2026-02-12 đến 2026-08-01.

---

## 5. Data Quality sau khi Clean

| Check | Dimension | Kết quả | Ghi chú |
|-------|-----------|---------|---------|
| row_count >= 1 | completeness | PASSED (24) | Đủ dữ liệu |
| paper_id not null | completeness | PASSED (0 nulls) | DOI luôn có |
| paper_id unique | uniqueness | PASSED (0 duplicates) | Không trùng lặp |
| title not null/empty | completeness | PASSED | Đã filter ở bước 3 |
| summary not empty | completeness | PASSED | Đã filter ở bước 3 |
| freshness <= 180 days | timeliness | PASSED (0 stale) | Tất cả đều fresh |
