# Luồng Thu Thập & Xử Lý Tin Tuyển Dụng: Từ Đường Dẫn Web Đến SQLite

Tài liệu này giải thích chi tiết các bước xảy ra bên trong khi người dùng hoặc AI Agent đưa vào một đường dẫn tuyển dụng (Job URL): hệ thống chọn bộ điều hợp nào, cơ chế vượt qua các trang web động (JavaScript/SPA) ra sao, cách chuẩn hóa dữ liệu, và quy trình khử trùng lặp trong cơ sở dữ liệu cục bộ.

---

## 1. Sơ đồ Luồng Thu Thập JD

```
[ Người dùng / Agent nhập URL ]
  (Greenhouse, ITviec, Indeed, hoặc web bất kỳ)
            |
            v
[ BƯỚC 1: Phân giải Bộ Điều Hợp (Adapter Resolution) ]
   - Trích xuất hostname từ URL (urlparse)
   - Quét qua danh sách adapter đã đăng ký theo thứ tự ưu tiên:
       1. GreenhouseAdapter (*.greenhouse.io)
       2. ITviecAdapter (itviec.com)
       3. IndeedAdapter (*.indeed.com)
       4. GenericAdapter (Fallback cho mọi domain khác)
            |
            v
[ BƯỚC 2: Tải Nội Dung & Đối Phó Web Động (Fetch Engine) ]
   - Chế độ HTTP Tĩnh (Mặc định):
       * httpx.Client gửi GET request kèm Modern Browser User-Agent
       * Tự động xử lý redirect và kiểm tra HTTP status code
   - Chế độ Trình duyệt Headless (--browser):
       * Kích hoạt Chromium qua Playwright
       * Chờ sự kiện `networkidle` để tải xong dữ liệu AJAX/SPA
       * Lấy toàn bộ DOM sau khi JavaScript đã render
            |
            v
[ BƯỚC 3: Bóc Tách & Chuẩn Hóa Cấu Trúc (Parsing & Normalization) ]
   - Bóc tách theo đặc thù từng trang:
       * Greenhouse: Thẻ h1.app-title, span.company-name, khối #content
       * ITviec: Kiểm tra Cloudflare challenge, bóc tách Description/Skills/Benefits
       * Indeed: Ưu tiên schema JSON-LD JobPosting, window._initialData, fallback DOM
       * Generic: Thẻ OpenGraph (og:title, og:site_name), thẻ ngữ nghĩa (<main>, <article>)
   - Tổng hợp văn bản hoàn chỉnh: `freeform_text`
            |
            v
[ BƯỚC 4: Băm Định Danh & Sinh ID Tự Động (Identity Fingerprinting) ]
   - Chuẩn hóa văn bản bằng `normalize_job_content()`
   - Tính toán mã băm SHA-256: `content_hash = hash_job_identity(freeform_text)`
   - Sinh mã định danh chuẩn: `job_id = job_<16 ký tự đầu của content_hash>`
            |
            v
[ BƯỚC 5: Lưu Trữ & Khử Trùng Lặp Cục Bộ (Persistence & Deduplication) ]
   - Lệnh ngầm: `CareerRepository.upsert_job(dedupe_by_source_identity=True)`
   - Khóa duy nhất theo URL gốc (`source_identity`)
   - Nếu JD đã tồn tại: Cập nhật nội dung mới, giữ nguyên trạng thái ứng tuyển cũ
   - Nếu JD mới: Tạo bản ghi mới, gán `applied = False`
```

---

## 2. Chi tiết Từng Bước

### Bước 1: Phân giải Bộ Điều Hợp (`find_adapter`)
- **Hành động:** Khi nhận URL (ví dụ: `https://itviec.com/it-jobs/senior-python-dev`), hàm `find_adapter(url)` quét qua danh sách `_ADAPTERS` trong `registry.py`.
- **Cơ chế:** Kiểm tra domain bằng `adapter.supports_url(url)`. Nếu không khớp adapter chuyên biệt nào, hệ thống tự động chỉ định `GenericAdapter` làm fallback an toàn.

### Bước 2: Tải Dữ liệu & Đối Phó Web Động
- **HTTP Tĩnh (`httpx`):** Được sử dụng mặc định để tối ưu tốc độ (chỉ mất vài trăm mili-giây).
- **Trình duyệt Headless (`Playwright`):** Khi người dùng gắn cờ `--browser` hoặc trang web dùng React/Vue để render dữ liệu client-side:
  - Khởi chạy Chromium ở chế độ nền.
  - Thiết lập User-Agent của máy tính để bàn.
  - Lắng nghe đường truyền mạng cho đến khi không còn request nền (`wait_until="networkidle"`).
  - Thu thập toàn bộ HTML hoàn chỉnh sau khi script chạy xong.

### Bước 3: Bóc Tách & Chuẩn Hóa Dữ Liệu
Mỗi adapter áp dụng chiến lược riêng để lấy thông tin sạch nhất:
- **Indeed:** Ưu tiên đọc cấu trúc `application/ld+json`. Cấu trúc này chứa dữ liệu nguyên bản do nhà tuyển dụng gửi lên Google/Search Engines, không bị ảnh hưởng bởi thay đổi giao diện HTML.
- **ITviec:** Kiểm tra các dấu hiệu của Cloudflare challenge (`cf-challenge`, `hcaptcha`). Nếu phát hiện trang bị chặn bot, adapter lập tức ném lỗi rõ ràng thay vì lưu HTML rác vào database.
- **Tạo `freeform_text`:** Ghép tiêu đề, công ty, địa điểm, URL và mô tả thành một khối văn bản duy nhất để phục vụ bước bóc tách yêu cầu sau này.

### Bước 4: Tính Toán Mã Băm Nhận Dạng
- Không dùng ID ngẫu nhiên. Mọi JD đều được định danh bằng nội dung thực tế của nó.
- `hash_job_identity(freeform_text)` tạo ra mã băm 64 ký tự hex.
- `job_id` được đặt tên theo quy tắc: `job_<16 hex đầu>`. Điều này đảm bảo tính nhất quán tuyệt đối giữa các lần quét.

### Bước 5: Lưu Trữ Cục Bộ & Khử Trùng Lặp
- Dữ liệu được ghi vào bảng `jobs` trong SQLite cục bộ (`careerviet.sqlite3`).
- Trường `source_identity` (chính là URL) đảm bảo rằng nếu bạn crawl lại một tin tuyển dụng nhiều lần, hệ thống sẽ tự động cập nhật bản ghi hiện có (`existing`) thay vì sinh ra nhiều bản sao trùng lặp.
