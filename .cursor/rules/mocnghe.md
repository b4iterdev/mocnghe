---
description: "Mốc Nghề CLI & Career Operations agent rules"
globs: ["*"]
---

# Mốc Nghề Agent Instructions

Khi người dùng hoặc agent đưa ra các lệnh dạng Slash Commands, ánh xạ và thực thi bằng công cụ terminal qua CLI `mocnghe`:

## Slash Commands & Workflows

### 1. `/crawl <url>` hoặc `/mocnghe-crawl <url>`
Crawl và import JD từ đường dẫn web (hỗ trợ Greenhouse, ITviec, Indeed, và các trang thông dụng):
```bash
uv run mocnghe [--workspace <path>] jobs crawl "<url>" [--browser]
```
- **Fallback (Nhập trực tiếp từ text/file):** Nếu trang web là dynamic SPA phức tạp hoặc crawler thiếu trường:
  ```bash
  uv run mocnghe [--workspace <path>] import-jd --file <path_to_jd.txt>
  # hoặc qua stdin:
  cat jd.txt | uv run mocnghe [--workspace <path>] import-jd --stdin
  ```
- **Cài đặt trình duyệt Crawler:** `--browser` yêu cầu Playwright Chromium:
  ```bash
  uv pip install -e ".[browser]" && uv run playwright install chromium
  ```

### 2. `/mocnghe-batch-crawl` hoặc `/batch-crawl`
Quét tự động diện rộng hàng loạt JD từ danh sách URLs với độ trễ an toàn tránh bị rate limit:
```bash
uv run mocnghe [--workspace <path>] jobs batch-crawl --file <seeds.txt> [--delay 0.5] [--browser] [--output <summary.json>]
# Hoặc truyền từng URL:
uv run mocnghe [--workspace <path>] jobs batch-crawl --url <url1> --url <url2>
```

### 3. `/search` hoặc `/mocnghe-search`
Tìm kiếm việc làm từ nguồn tuyển dụng:
```bash
uv run mocnghe [--workspace <path>] jobs search --source itviec --live --keyword "<keyword>" --location "<location>"
```

### 4. `/onboard` hoặc `/mocnghe-onboard`
Xác nhận hoặc cập nhật hồ sơ ứng viên từ `profile.json`:
1. Kiểm tra tính hợp lệ của schema:
   ```bash
   uv run mocnghe [--workspace <path>] profile validation
   ```
2. Xác nhận và lưu vào CSDL SQLite:
   ```bash
   uv run mocnghe [--workspace <path>] profile confirm-file
   ```
- **Lưu ý quan trọng (Pitfall):** Các phiên bản profile đã confirmed là bất biến (`ValueError: confirmed profile versions are immutable`). Phải tăng trường `version` trong `profile.json` (ví dụ `1.0` -> `1.1` hoặc timestamp) trước khi chạy `confirm-file` khi cập nhật hồ sơ đã tồn tại.

### 5. `/triage <job_id>` hoặc `/mocnghe-triage <job_id>`
Đánh giá độ phù hợp (triage) giữa hồ sơ ứng viên và JD:
```bash
uv run mocnghe [--workspace <path>] evaluate triage <job_id>
```
- **Checklist đánh giá:**
  1. **Lịch biểu & Tính khả dụng (Blocker hàng đầu):** Đối chiếu thời gian tốt nghiệp và lịch học với yêu cầu (toàn thời gian onsite vs thực tập bán thời gian linh hoạt).
  2. **Độ tương thích năng lực lõi:** Đối chiếu ngôn ngữ lập trình, hệ thống (C++, Python, TypeScript, Linux, Docker, networking).
  3. **Mức lương sàn:** Đảm bảo phù hợp mức kỳ vọng của ứng viên.

### 6. `/tailor <job_id>` hoặc `/mocnghe-tailor <job_id>`
Khởi tạo và tinh chỉnh bản CV xuất bản định dạng PDF:
1. Xem danh sách các bản thảo CV hiện có:
   ```bash
   uv run mocnghe [--workspace <path>] cv list
   uv run mocnghe [--workspace <path>] cv review <cv_id>
   ```
2. Tạo bản CV ban đầu gắn với các evidence IDs:
   ```bash
   uv run mocnghe [--workspace <path>] cv create --profile-version <ver> --language <en|vi> --job-id <job_id> \
     --identity name --identity email --identity linkedin --identity github --identity location \
     --evidence <ev_id_1> --evidence <ev_id_2> ...
   ```
3. Xem xét mã băm SHA-256 và duyệt nội dung:
   ```bash
   uv run mocnghe [--workspace <path>] cv review <cv_id>
   uv run mocnghe [--workspace <path>] cv approve <cv_id> --hash <content_hash>
   ```
4. Xuất gói hồ sơ CV (thư mục chứa `cv.pdf`, `cv.html`, `cv.json`):
   ```bash
   uv run mocnghe [--workspace <path>] cv export <cv_id> --output <output_dir> [--engine modern|reportlab] [--max-pages 2]
   ```
   * *Ghi chú:* `--engine modern` (mặc định) sử dụng Playwright HTML/CSS với gradient header và badge tags theo phong cách career-ops. `--engine reportlab` là engine thuần Python dựng bằng canvas.

### 7. `/mocnghe-visual-test <cv_id>` hoặc `/visual-test <cv_id>`
Kiểm thử hồi quy trực quan cho file PDF tránh vỡ layout hoặc tràn trang:
```bash
uv run mocnghe [--workspace <path>] cv verify-visual <cv_id> --snapshot <snapshot.png> [--update] [--tolerance 0.01]
```

### 8. `/cover-letter <job_id>` hoặc `/mocnghe-cover-letter <job_id>`
Tạo thư xin việc gắn với bằng chứng CV đã duyệt:
1. Tạo cover letter:
   ```bash
   uv run mocnghe [--workspace <path>] cover-letter create --cv-id <cv_id> --job-id <job_id> [--recipient "<name/team>"]
   ```
2. Xem xét mã băm và phê duyệt:
   ```bash
   uv run mocnghe [--workspace <path>] cover-letter review <cl_id>
   uv run mocnghe [--workspace <path>] cover-letter approve <cl_id> --hash <content_hash>
   ```
3. Xuất gói thư xin việc (`cover_letter.pdf`, `cover_letter.md`, `cover_letter.txt`, `cover_letter.json`):
   ```bash
   uv run mocnghe [--workspace <path>] cover-letter export <cl_id> --output <output_dir> [--max-pages 1]
   ```

### 9. `/track [job_id] [state]` hoặc `/mocnghe-track [job_id] [state]`
Xem danh sách đơn hoặc cập nhật trạng thái tracking:
```bash
# Xem danh sách
uv run mocnghe [--workspace <path>] applications list
# Cập nhật trạng thái tuần tự (discovered -> shortlisted -> drafting -> ready -> applied)
uv run mocnghe [--workspace <path>] track <job_id> --state <state> [--cv <cv_id>]
```
- **Lưu ý:** Quá trình chuyển trạng thái là máy trạng thái tuyến tính (Finite State Machine). Không được nhảy cóc từ `discovered` lên thẳng `ready`. Chuyển sang `applied` cần người dùng xác nhận đã nộp thủ công thực tế.
