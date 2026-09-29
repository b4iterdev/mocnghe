# Mốc Nghề Agent Instructions

Khi người dùng hoặc agent đưa ra các lệnh dạng Slash Commands, ánh xạ và thực thi bằng công cụ terminal qua CLI `mocnghe`:

## Slash Commands

### `/crawl <url>` hoặc `/mocnghe-crawl <url>`
Crawl và import JD từ đường dẫn web (hỗ trợ Greenhouse, ITviec, Indeed, và các trang thông dụng):
```bash
uv run mocnghe jobs crawl "<url>"
# Thêm --browser nếu trang yêu cầu render JavaScript hoặc bị chặn
uv run mocnghe jobs crawl "<url>" --browser
```

### `/onboard` hoặc `/mocnghe-onboard`
Xác nhận hoặc cập nhật hồ sơ ứng viên từ `profile.json`:
```bash
uv run mocnghe profile confirm-file
```

### `/triage <job_id>` hoặc `/mocnghe-triage <job_id>`
Đánh giá độ phù hợp (triage) giữa hồ sơ ứng viên và JD:
```bash
uv run mocnghe evaluate triage <job_id>
```

### `/tailor <job_id>` hoặc `/mocnghe-tailor <job_id>`
Khởi tạo và tinh chỉnh bản CV xuất bản định dạng PDF:
1. Tạo bản CV ban đầu:
   ```bash
   uv run mocnghe cv create --profile-version 1.0 --language en --job-id <job_id> --identity full_name --identity email --identity linkedin --identity github --identity location --evidence <ev_id> ...
   ```
2. Rà soát, duyệt nội dung và xuất PDF:
   ```bash
   uv run mocnghe cv review <cv_id>
   uv run mocnghe cv approve <cv_id> --hash <content_hash>
   uv run mocnghe cv export <cv_id> --output cv_tailored.pdf --max-pages 2
   ```

### `/track [job_id] [state]` hoặc `/mocnghe-track [job_id] [state]`
Xem danh sách đơn hoặc cập nhật trạng thái tracking:
```bash
# Xem danh sách
uv run mocnghe applications list
# Cập nhật trạng thái (discovered -> shortlisted -> drafting -> ready -> applied)
uv run mocnghe track <job_id> --state <state>
```
