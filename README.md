# 🌿 Mốc Nghề (mocnghe)

> **Trợ lý tìm việc & may đo hồ sơ ứng tuyển cá nhân hóa — Local-first, minh bạch và chống bịa đặt.**

Mốc Nghề là công cụ dòng lệnh (CLI) và bộ kỹ năng AI Agent hỗ trợ trọn vẹn chu trình tìm việc cho ứng viên tại Việt Nam: từ thu thập tin tuyển dụng, đánh giá độ phù hợp (triage), may đo CV & Cover Letter theo chuẩn ATS/Modern, cho đến quản lý trạng thái nộp đơn.

---

## ✨ Điểm Nổi Bật

- 🔒 **Local-First & Bảo Mật Quyền Riêng Tư:** Toàn bộ dữ liệu hồ sơ, lịch sử nộp đơn lưu cục bộ trong CSDL SQLite (`careerviet.sqlite3`). Dữ liệu danh tính cá nhân không bị gửi lên mạng khi phân tích job.
- 🎯 **Grounded Evidence (Không Bịa Đặt):** Mọi kinh nghiệm, kỹ năng trên CV và Cover Letter đều phải xuất phát từ bằng chứng thực tế đã xác nhận (`CandidateEvidence`). Tuyệt đối không sinh số liệu ảo (hallucination).
- 🎨 **Render Đẹp & Chuẩn ATS:** Hỗ trợ cả 2 engine xuất PDF:
  - `--engine modern`: Giao diện hiện đại (HTML/CSS + Playwright) với dải màu gradient, thẻ năng lực trực quan (phong cách tương tự *career-ops*).
  - `--engine reportlab`: Engine native Python nhẹ, ổn định, hỗ trợ tiếng Việt có dấu hoàn chỉnh.
- 📬 **Cover Letter Tự Động:** Tự động sinh thư ứng tuyển chuyên nghiệp (Anh/Việt) liên kết chặt chẽ với những kinh nghiệm phù hợp nhất với vị trí.
- 📊 **Theo Dõi Đơn Tuyển Dụng Tuyến Tính:** Quản lý phễu ứng tuyển có kiểm soát (`discovered` → `shortlisted` → `drafting` → `ready` → `applied`). Người dùng luôn giữ quyền kiểm soát tối thượng khi gửi đơn (human-in-the-loop).

---

## 🚀 Hướng Dẫn Bắt Đầu Nhanh (5 Phút)

### 1. Cài đặt môi trường

Yêu cầu: Python `>= 3.12` và [uv](https://docs.astral.sh/uv/).

```bash
# Clone repository
git clone git@github.com:b4iterdev/mocnghe.git
cd mocnghe

# Cài đặt thư viện
uv sync

# (Tùy chọn) Cài đặt trình duyệt cho tính năng Render Modern & Web Crawler
uv pip install -e ".[browser]"
uv run playwright install chromium
```

### 2. Khởi tạo Không gian làm việc (Workspace)

Mặc định Mốc Nghề sử dụng thư mục `data/` làm workspace:

```bash
uv run mocnghe --workspace data init
```

### 3. Nạp Hồ sơ Ứng viên (Onboarding)

Tạo file `data/profile.json` chứa thông tin cá nhân và danh sách các bằng chứng năng lực (xem mẫu tại `tests/fixtures/synthetic_profile.json`), sau đó xác nhận vào hệ thống:

```bash
# Kiểm tra định dạng hồ sơ
uv run mocnghe --workspace data profile validation

# Xác nhận và lưu vào CSDL
uv run mocnghe --workspace data profile confirm-file
```

---

## 🛠️ Quy Trình Sử Dụng Hàng Ngày

```
  [1. Thu thập JD]  ──>  [2. Đánh giá Triage]  ──>  [3. May đo CV & Cover Letter]  ──>  [4. Theo dõi Đơn]
  crawl / import         evaluate triage            cv / cover-letter               track / apply
```

### Bước 1: Thu thập Tin tuyển dụng (JD)

Hỗ trợ lấy tin trực tiếp từ đường dẫn (ITviec, Greenhouse, Indeed, ...) hoặc nhập file văn bản:

```bash
# Crawl trực tiếp từ URL
uv run mocnghe --workspace data jobs crawl "https://itviec.com/it-jobs/..."

# Quét hàng loạt diện rộng từ file danh sách URL
uv run mocnghe --workspace data jobs batch-crawl --file urls.txt --delay 0.5

# Hoặc nhập từ file văn bản / sao chép từ clipboard
uv run mocnghe --workspace data import-jd --file my_jd.txt
cat my_jd.txt | uv run mocnghe --workspace data import-jd --stdin
```

Xem danh sách việc làm đã lưu:
```bash
uv run mocnghe --workspace data jobs list
uv run mocnghe --workspace data jobs show <job_id>
```

### Bước 2: Đánh giá độ phù hợp (Triage)

Sàng lọc nhanh xem công việc có thỏa mãn các tiêu chí cứng (địa điểm, thời gian làm việc, mức lương sàn, kỹ năng cốt lõi) hay không:

```bash
uv run mocnghe --workspace data evaluate triage <job_id>
```

### Bước 3: Tạo & Xuất CV Cá nhân hóa

Chọn các bằng chứng năng lực (`--evidence`) phù hợp nhất với JD:

```bash
# 1. Tạo bản thảo CV
uv run mocnghe --workspace data cv create \
  --profile-version 1.0 \
  --language en \
  --job-id <job_id> \
  --identity name --identity email --identity linkedin --identity github --identity location \
  --evidence ev_camera --evidence ev_web --evidence ev_education

# 2. Xem lại nội dung và lấy mã băm an toàn (content_hash)
uv run mocnghe --workspace data cv review <cv_id>

# 3. Phê duyệt nội dung CV (bảo vệ chống giả mạo)
uv run mocnghe --workspace data cv approve <cv_id> --hash <content_hash>

# 4. Xuất trọn bộ bundle CV (PDF + HTML + JSON)
uv run mocnghe --workspace data cv export <cv_id> --output output/my_cv --engine modern --max-pages 2

# 5. Kiểm thử trực quan tránh tràn trang / vỡ bố cục
uv run mocnghe --workspace data cv verify-visual <cv_id> --snapshot output/my_cv/snapshot.png
```

### Bước 4: Tạo Thư ứng tuyển (Cover Letter)

Sinh Cover Letter song ngữ dựa trên các nội dung đã được duyệt trong CV:

```bash
# Tạo bản thảo thư xin việc
uv run mocnghe --workspace data cover-letter create --cv-id <cv_id> --job-id <job_id> --recipient "Hiring Team"

# Duyệt nội dung
uv run mocnghe --workspace data cover-letter approve <cl_id> --hash <content_hash>

# Xuất file (PDF, Markdown, TXT)
uv run mocnghe --workspace data cover-letter export <cl_id> --output output/my_cover_letter
```

### Bước 5: Quản lý Phễu Ứng tuyển (Tracking)

Theo dõi chặt chẽ tiến trình qua từng giai đoạn:

```bash
# Chuyển trạng thái theo dõi
uv run mocnghe --workspace data track <job_id> --state shortlisted
uv run mocnghe --workspace data track <job_id> --state drafting
uv run mocnghe --workspace data track <job_id> --state ready --cv <cv_id>

# Sau khi đã nộp thủ công trên website của nhà tuyển dụng:
uv run mocnghe --workspace data apply <job_id> --cv <cv_id> --confirm

# Cập nhật kết quả phỏng vấn / phản hồi
uv run mocnghe --workspace data track <job_id> --state interviewing
uv run mocnghe --workspace data applications list
```

---

## 🤖 Sử Dụng Cùng AI Coding Agent (Hermes, Claude Code, Cursor)

Mốc Nghề được thiết kế để điều khiển hoàn toàn bằng Slash Commands qua AI Agent:

| Lệnh | Ý nghĩa |
| :--- | :--- |
| `/mocnghe-crawl <url>` | Bóc tách và lưu JD từ trang tuyển dụng |
| `/mocnghe-batch-crawl` | Quét tự động danh sách hạt giống URLs |
| `/mocnghe-onboard` | Kiểm tra và cập nhật hồ sơ ứng viên |
| `/mocnghe-triage <job_id>` | Đánh giá mức độ phù hợp giữa bạn và JD |
| `/mocnghe-tailor <job_id>` | Tạo, may đo và xuất bản CV PDF hoàn chỉnh |
| `/mocnghe-cover-letter <job_id>` | Sinh thư xin việc gắn kèm bằng chứng năng lực |
| `/mocnghe-visual-test <cv_id>` | Kiểm định trực quan ảnh snapshot PDF |
| `/mocnghe-track <job_id> <state>` | Xem và chuyển trạng thái hồ sơ ứng tuyển |

---

## 🔧 Cấu Hình Nâng Cao & Tích Hợp AI Provider

Nếu muốn sử dụng mô hình LLM ngoài (như OpenAI, 9Router, DeepSeek) để gợi ý diễn đạt hoặc đánh giá chuyên sâu:

```bash
export MOCNGHE_EVAL_ENDPOINT="https://api.openai.com/v1/chat/completions"
export MOCNGHE_EVAL_MODEL="gpt-4o-mini"
export MOCNGHE_EVAL_API_KEY="sk-..."
```

*Lưu ý:* Mốc Nghề luôn tự động loại bỏ thông tin định danh cá nhân (PII) trước khi tạo gói gửi cho AI.

---

## 📚 Tài Liệu Kỹ Thuật & Kiến Trúc

- 📑 [Luồng Xử lý Hồ sơ & May đo CV (Chi tiết)](docs/cv_processing_lifecycle_vi.md)
- 🌐 [Cơ chế Thu thập & Adapter Bóc tách JD](docs/job_crawling_lifecycle_vi.md)
- 🎯 [Máy Trạng Thái Ứng Tuyển & Tracking](docs/application_tracking_lifecycle_vi.md)
- 🏛️ [Kiến trúc Toàn Hệ Thống (Architecture Guide)](docs/architecture_and_operations_vi.md)

---

## 🧪 Kiểm Thử Hệ Thống

```bash
# Chạy toàn bộ test suite
uv run pytest -q

# Kiểm tra định dạng code & chuẩn linter
uv run ruff check .
```

---

## 📄 Bản Quyền & Giấy Phép

Phát triển bởi **Thai & Hermes**. Mã nguồn được phát hành theo giấy phép mã nguồn mở MIT.
