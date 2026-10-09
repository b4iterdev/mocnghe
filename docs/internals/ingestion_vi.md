# Ingestion Subsystem (Phân hệ Thu thập Dữ liệu)

Phân hệ `ingestion` chịu trách nhiệm thu nạp tin tuyển dụng (Job Description - JD) từ nhiều nguồn khác nhau (tệp văn bản, stdin, HTTP API, và trình duyệt tự động), chuẩn hóa dữ liệu về mô hình `Job` thống nhất và ghi nhận nguồn gốc xuất xứ (`SourceProvenance`).

---

## 1. Kiến trúc Tổng thể

```
                 +-----------------------------------------------+
                 |                   Nguồn Đầu Vào               |
                 |      URL web / Tệp text / Stdin / Fixtures     |
                 +-----------------------+-----------------------+
                                         |
                                         v
                         +-------------------------------+
                         |      Registry (registry.py)   |
                         |   find_adapter(url) -> Adapter|
                         +---------------+---------------+
                                         |
         +-------------------------------+-------------------------------+
         |                               |                               |
         v                               v                               v
[ GreenhouseAdapter ]            [ ITviecAdapter ]               [ IndeedAdapter ]
  - Domain matching               - Cloudflare challenge check    - JSON-LD Schema
  - DOM selector parsing          - Section splitting             - window._initialData
         |                               |                               |
         +-------------------------------+-------------------------------+
                                         | (fallback nếu domain lạ)
                                         v
                                 [ GenericAdapter ]
                                  - OpenGraph / Meta
                                  - Semantic HTML
                                         |
                                         v
                 +-----------------------------------------------+
                 |           Cơ chế Tải Dữ liệu (Fetch)          |
                 |  - HTTP tĩnh: httpx.Client (có timeout & UA)  |
                 |  - Dynamic: Playwright headless browser       |
                 +-----------------------+-----------------------+
                                         |
                                         v
                 +-----------------------------------------------+
                 |           Chuẩn hóa & Băm Nhận dạng           |
                 |  - freeform_text aggregation                  |
                 |  - hash_job_identity() -> SHA-256             |
                 |  - job_id_from_hash() -> "job_<16 hex>"       |
                 +-----------------------+-----------------------+
                                         |
                                         v
                         CareerRepository.upsert_job()
```

---

## 2. Các Thành phần Chi tiết

### 2.1. Lớp Cơ sở `BaseJobAdapter` (`adapters/base.py`)
Mọi adapter phải kế thừa từ lớp trừu tượng này:
- `name: str`: Định danh adapter (ví dụ: `"greenhouse"`, `"itviec"`).
- `domains: tuple[str, ...]`: Danh sách domain khớp (ví dụ: `("greenhouse.io",)`). Nếu rỗng, adapter chấp nhận mọi URL (dùng cho generic fallback).
- `supports_url(url: str) -> bool`: Kiểm tra hostname của URL có thuộc `domains` hay không.
- `parse_job(content: str, *, url: str) -> Job`: Hàm thuần túy biến chuỗi HTML/JSON thành đối tượng `Job`.
- `fetch_job(url: str, *, use_browser: bool, timeout_seconds: float) -> Job`: Điều phối việc tải trang:
  - Mặc định: Dùng `httpx.Client` với User-Agent giả lập trình duyệt hiện đại.
  - Khi `use_browser=True`: Ủy quyền cho `fetch_rendered_html` của Playwright.

### 2.2. Trình duyệt Headless `browser.py`
- Được thiết kế dưới dạng **Optional Extra**: Sử dụng `importlib.import_module("playwright.sync_api")` tại thời điểm chạy (runtime).
- Nếu người dùng chưa cài `mocnghe[browser]`, hệ thống ném ngoại lệ rõ ràng với hướng dẫn cài đặt cụ thể thay vì gây crash khó hiểu.
- Cấu hình: Khởi chạy Chromium ở chế độ `headless=True`, đợi sự kiện `networkidle` để đảm bảo các Single Page Application (SPA) đã tải xong dữ liệu qua AJAX.

### 2.3. Các Adapter Chuyên biệt
- **`GreenhouseAdapter`**: Bóc tách thẻ `<h1 class="app-title">`, công ty từ `<span class="company-name">` hoặc từ URL path token (`/<company>/jobs/<id>`), gom toàn bộ nội dung khối `#content`.
- **`ITviecAdapter`**:
  - Nhận diện bot challenge qua kiểm tra chuỗi (`cf-challenge`, `hcaptcha`, v.v.).
  - Bóc tách theo từng khối tiêu đề: Mô tả (`job description`), Kỹ năng yêu cầu (`your skills`), Quyền lợi (`benefits`).
- **`IndeedAdapter`**:
  - Chiến lược 1: Tìm kiếm thẻ `<script type="application/ld+json">` có schema `@type: "JobPosting"`. Đây là định dạng sạch nhất, không phụ thuộc vào thay đổi giao diện HTML.
  - Chiến lược 2: Regex bóc tách biến trạng thái `window._initialData`.
  - Chiến lược 3: Fallback bóc thẻ DOM (`#jobDescriptionText`).
- **`GenericAdapter`**: Fallback cho bất kỳ website nào bằng cách đọc OpenGraph metadata (`og:title`, `og:site_name`) và thẻ ngữ nghĩa (`<main>`, `<article>`).

---

## 3. Cơ chế Khử trùng lặp & Băm Dữ liệu (Deduplication)

Khi một JD được nạp:
1. Adapter tạo chuỗi văn bản hoàn chỉnh `freeform_text`.
2. Hàm `hash_job_identity(freeform_text)` chuẩn hóa khoảng trắng và tính mã SHA-256 (64 ký tự hex).
3. `job_id` được sinh ra tự động: `job_<16 ký tự đầu của SHA-256>`.
4. Trong SQLite, bảng `jobs` sử dụng `source_identity` (chính là URL hoặc đường dẫn file) làm khóa duy nhất khi kích hoạt `dedupe_by_source_identity=True`. Nếu JD đã tồn tại, hệ thống cập nhật nội dung thay vì tạo bản ghi rác.
