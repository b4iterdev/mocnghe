# Local Database & Storage Subsystem (Phân hệ Lưu trữ Dữ liệu Cục bộ)

Phân hệ lưu trữ của Mốc Nghề được hiện thực hóa qua lớp `CareerRepository` (`storage/repository.py`), sử dụng **SQLite 3** độc lập nằm trong từng workspace (`careerviet.sqlite3`). Toàn bộ hoạt động đều hướng tới tính toàn vẹn dữ liệu, kiểm tra băm SHA-256 chống can thiệp trái phép và hỗ trợ khôi phục dễ dàng.

---

## 1. Kiến trúc Bảng Dữ liệu (Database Schema)

```
+---------------------------------------------------------------------------------------------------+
|                                      careerviet.sqlite3 (SQLite)                                   |
+---------------------------------------------------------------------------------------------------+
|                                                                                                   |
|  [ jobs ]                                        [ profiles ]                                     |
|  - job_id (PK, text)                             - profile_id (PK, text)                          |
|  - source_id (text)                              - version (PK, text)                             |
|  - title, employer, location (text)              - payload_json (text)                            |
|  - description, requirements, benefits (text)    - content_hash (text, SHA-256)                   |
|  - freeform_text (text)                          - confirmed_at (text, ISO UTC)                   |
|  - content_hash (text, SHA-256)                  |                                                |
|  - applied (boolean)                             |                                                |
|                                                  |                                                |
|  [ profile_drafts ]                              [ evaluation_reports ]                           |
|  - draft_id (PK, text)                           - report_id (PK, text)                           |
|  - payload_json (text)                           - profile_version, job_id (text)                 |
|  - updated_at (text)                             - jd_content_hash (text)                         |
|                                                  - runtime, model, payload_json (text)            |
|                                                                                                   |
|  [ cv_revisions ]                                [ cv_approvals ]                                 |
|  - id (PK, text)                                 - id (PK, FK -> cv_revisions.id)                 |
|  - payload (text, JSON)                          - hash (text, SHA-256)                           |
|  - hash (text, SHA-256)                                                                           |
|                                                                                                   |
|  [ application_drafts ]                          [ application_draft_approvals ]                  |
|  - id (PK, text)                                 - id (PK, FK -> application_drafts.id)           |
|  - payload (text, JSON)                          - hash (text, SHA-256)                           |
|  - hash (text, SHA-256)                                                                           |
|                                                                                                   |
|  [ applications ]                                [ application_events ]                           |
|  - application_id (PK, int auto)                 - event_id (PK, int auto)                        |
|  - job_id (FK -> jobs.job_id)                    - application_id (FK -> applications)            |
|  - state (text, CHECK state IN (...))            - from_state, to_state (text)                    |
|  - cv_version (text)                             - created_at, note (text)                        |
|  - submission_json (text, snapshot)             - submission_hash (text)                         |
|  - submission_hash (text, SHA-256)                                                                |
+---------------------------------------------------------------------------------------------------+
```

---

## 2. Tính Tương thích Lưu trữ & Tên File Bất biến

- **Tên File SQLite Bất biến (`careerviet.sqlite3`):**
  Mặc dù dự án đã đổi tên thành **Mốc Nghề** (`mocnghe`), tên tệp cơ sở dữ liệu vật lý vẫn được cố ý giữ nguyên là `careerviet.sqlite3`.
  - **Lý do:** Tránh việc người dùng sau khi nâng cấp bị mở một database mới hoàn toàn trống rỗng, bảo vệ an toàn toàn bộ dữ liệu tuyển dụng đã lưu trong quá khứ.
- **Tính Độc lập của Workspace:**
  Mỗi thư mục workspace (mặc định là `data/`, hoặc chỉ định qua `--workspace <path>`) chứa cơ sở dữ liệu riêng biệt. Người dùng có thể sao lưu, di chuyển hoặc nén thư mục workspace mà không phụ thuộc vào dịch vụ máy chủ bên ngoài.

---

## 3. Cơ chế Khóa và Kiểm tra Băm (Audit & Tamper Detection)

### 3.1. Xác thực Mã băm khi Đọc (`digest` check)
Khi truy vấn một bản thảo CV từ bảng `cv_revisions`:
```python
row = db.execute("SELECT payload, hash FROM cv_revisions WHERE id=?", (cv_id,)).fetchone()
cv = CV.model_validate_json(row["payload"])
if digest(cv) != row["hash"]:
    raise ValueError("CV content hash mismatch")
```
Nếu có ai đó (hoặc một tiến trình bên ngoài) trực tiếp can thiệp và sửa nội dung cột `payload` trong SQLite, hàm tính toán lại mã băm `digest(cv)` sẽ không khớp với cột `hash`, hệ thống lập tức từ chối xử lý và ném lỗi vi phạm toàn vẹn.

### 3.2. Tính Bất biến của Phiên bản Hồ sơ (`profiles`)
Khi lưu hồ sơ chính thức qua `save_confirmed_profile()`:
- Câu lệnh `INSERT` kiểm tra trùng lặp phiên bản. Nếu cùng một `version` được ghi nhận lần thứ hai, hệ thống ném ngoại lệ `confirmed profile versions are immutable`.
- Hồ sơ một khi đã xác nhận thì không thể sửa; muốn cập nhật bắt buộc phải tăng số phiên bản.

### 3.3. Tự chẩn đoán Cơ sở Dữ liệu (`mocnghe doctor`)
Hàm `doctor()` trong `CareerRepository` thực hiện:
- Kiểm tra tính toàn vẹn của tệp SQLite (`PRAGMA integrity_check`).
- Kiểm tra tính hợp lệ của các ràng buộc khóa ngoại (`PRAGMA foreign_key_check`).
- Báo cáo số lượng bản ghi tin tuyển dụng và hồ sơ đang quản lý.
