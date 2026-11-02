# Local Storage Subsystem (Phân hệ Lưu trữ Dữ liệu Cục bộ)

Phân hệ lưu trữ của Mốc Nghề được hiện thực hóa qua lớp `CareerRepository` (`storage/repository.py`), sử dụng **Pure File-Based Storage** độc lập nằm trong từng workspace (mặc định là `data/`). Toàn bộ dữ liệu được lưu dưới dạng văn bản tĩnh (Markdown, YAML, JSON), kiểm tra băm SHA-256 chống can thiệp trái phép, kiểm soát tranh chấp đồng thời bằng file-lock hệ điều hành (`fcntl.flock`), và thân thiện 100% với Git tracking.

---

## 1. Cấu trúc Thư mục Workspace (Workspace Layout)

```
workspace/
├── .lock                          # Khóa tranh chấp đồng thời (fcntl.flock)
├── pipeline.md                    # Bảng theo dõi tiến trình tuyển dụng (Kanban board)
├── profile.json                   # Hồ sơ ứng viên nguồn
├── profiles/                      # Snapshot hồ sơ bất biến
│   ├── {version}.md               # Bản Markdown dễ đọc
│   └── {version}.yaml             # Schema Pydantic kèm fingerprint _hash
├── jobs/                          # Tin tuyển dụng đã thu thập
│   └── {job_id}.md                # YAML frontmatter + nội dung chi tiết JD
├── applications/                  # Tiến trình và audit trail nộp đơn
│   └── {job_id}.yaml              # State, CV version, snapshot, lịch sử events
├── cvs/                           # Bản may đo CV và phê duyệt
│   ├── {cv_id}.md                 # Bản CV định dạng Markdown
│   ├── {cv_id}.yaml               # Schema claims kèm _hash
│   └── {cv_id}.approval.yaml      # Bằng chứng phê duyệt của ứng viên (SHA-256)
├── cover_letters/                 # Thư xin việc
│   ├── {cl_id}.yaml               # Schema cover letter kèm _hash
│   └── {cl_id}.approval.yaml      # Phê duyệt thư xin việc
├── drafts/                        # Bản nháp biểu mẫu ứng tuyển
│   ├── {draft_id}.yaml            # Bản nháp form/email
│   └── {draft_id}.approval.yaml   # Phê duyệt bản nháp
├── reports/                       # Báo cáo đánh giá (Triage & Matching)
│   ├── {report_id}.md             # Báo cáo Markdown
│   └── {report_id}.yaml           # Dữ liệu đánh giá có cấu trúc
└── observations/                  # Lịch sử quan sát nguồn JD
    └── {job_id}.json              # Dữ liệu raw_content và URL gốc
```

---

## 2. Tính Tương thích Lưu trữ & Triết lý Git-friendly

- **Không còn phụ thuộc binary SQLite:**
  Trước đây dự án sử dụng `careerviet.sqlite3`. Hiện tại, toàn bộ dữ liệu đã chuyển dịch hoàn toàn sang tệp văn bản thuần túy (`.md` và `.yaml`).
  - **Lợi ích:** Người dùng có thể dễ dàng kiểm tra lịch sử qua Git (`git diff`, `git log`), sao lưu qua đám mây riêng hoặc chỉnh sửa trực tiếp mà không gặp rủi ro hỏng cơ sở dữ liệu binary.
- **Tính Độc lập của Workspace:**
  Mỗi thư mục workspace (mặc định là `data/`, hoặc chỉ định qua `--workspace <path>`) chứa toàn bộ trạng thái riêng biệt. Người dùng có thể sao lưu, di chuyển hoặc nén thư mục workspace mà không phụ thuộc vào bất kỳ dịch vụ máy chủ bên ngoài nào.

---

## 3. Cơ chế Khóa và Kiểm tra Băm (Audit & Tamper Detection)

### 3.1. Xác thực Mã băm khi Đọc (`digest` check)
Khi truy vấn một bản thảo CV từ tệp `cvs/{cv_id}.yaml`:
```python
data = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
stored_hash = data.pop("_hash", None)
cv = CV.model_validate(data)
if stored_hash is not None and digest(cv) != stored_hash:
    raise ValueError("CV content hash mismatch")
```
Nếu có ai đó (hoặc một tiến trình bên ngoài) trực tiếp can thiệp và sửa nội dung claim trong file YAML mà không qua luồng phê duyệt, hàm tính toán lại mã băm `digest(cv)` sẽ không khớp với `stored_hash`, hệ thống lập tức từ chối xử lý và ném lỗi vi phạm toàn vẹn.

### 3.2. Tính Bất biến của Phiên bản Hồ sơ (`profiles`)
Khi lưu hồ sơ chính thức qua `save_confirmed_profile()`:
- Hệ thống kiểm tra sự tồn tại của tệp `profiles/{version}.yaml`. Nếu cùng một `version` đã tồn tại, hệ thống ném ngoại lệ `confirmed profile versions are immutable`.
- Hồ sơ một khi đã xác nhận thì không thể sửa đè; muốn cập nhật bắt buộc phải tăng số phiên bản.

### 3.3. Kiểm soát Tranh chấp Đồng thời (Concurrency Locking)
Thay vì dùng transaction khóa bảng SQLite, Mốc Nghề sử dụng khóa tệp OS qua `fcntl.flock` trên tệp `.lock`:
```python
@contextmanager
def lock(self):
    self.initialize()
    with open(self.lock_file, "w") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(f, fcntl.LOCK_UN)
```

### 3.4. Tự chẩn đoán Workspace (`mocnghe doctor`)
Hàm `doctor()` trong `CareerRepository` thực hiện:
- Kiểm tra tính hợp lệ và cấu trúc các thư mục con trong workspace.
- Đếm số lượng tin tuyển dụng, hồ sơ, đơn ứng tuyển và báo cáo đang quản lý trên đĩa.
