# Kiến Trúc & Hướng Dẫn Vận Hành Mốc Nghề (mocnghe)

Mốc Nghề là hệ thống **local-first career operations**, hỗ trợ tự động hóa và quản lý toàn bộ chu trình tìm việc, đánh giá độ phù hợp (triage), tinh chỉnh CV (tailoring), và theo dõi đơn ứng tuyển (application tracking).

Tài liệu này được thiết kế để con người (lập trình viên, người tìm việc, hoặc quản trị viên) có thể nhanh chóng nắm bắt cấu trúc và vận hành hệ thống cùng AI Agent.

---

## 1. Triết lý Thiết kế Cốt lõi (Design Principles)

1. **Local-First & Quyền riêng tư:**
   - Dữ liệu ứng viên, lịch sử nộp đơn, và hồ sơ được lưu hoàn toàn trên máy cục bộ (`SQLite`).
   - Không tự động gửi email hay submit form. Người dùng giữ quyền kiểm soát tối thượng (`human-controlled submissions`).
2. **Evidence-Grounded (Có dẫn chứng thực tế):**
   - Mọi thông tin trên CV hoặc bản giải trình đều phải bắt nguồn từ bằng chứng có thật (`CandidateEvidence`).
   - Tuyệt đối không sinh số liệu giả (hallucinated metrics), không tự biến thực tập/tình nguyện thành kinh nghiệm làm việc chính thức.
3. **Audit & Chống giả mạo (Tamper-evident):**
   - Mọi phiên bản CV và snapshot đơn ứng tuyển đều được gắn mã băm SHA-256 (`content_hash`). Bất kỳ sự thay đổi trực tiếp nào trong database mà không qua quy trình review đều bị từ chối.
4. **Agent & CLI Đồng bộ:**
   - Mọi thao tác có thể thực hiện thông qua CLI độc lập hoặc thông qua AI Agent bằng Slash Commands.

---

## 2. Bản đồ Kiến trúc Hệ thống

```
                                    +-----------------------------------------+
                                    |        Giao diện Người dùng & Agent     |
                                    |  (CLI / Cursor Rules / Hermes Skills)   |
                                    +--------------------+--------------------+
                                                         |
                                 +-----------------------+-----------------------+
                                 |                                               |
                                 v                                               v
                     [ Ingestion Subsystem ]                         [ Candidate & Career Subsystem ]
            +---------------------------------------+               +---------------------------------------+
            |  - Modular Adapters:                  |               |  - Profile: Evidence & Facts Storage  |
            |    * Greenhouse, ITviec, Indeed       |               |  - Triage Engine: Fit Evaluation      |
            |    * Generic Fallback (Metadata/DOM)  |               |  - CV Engine: Revisions & PDF Render  |
            |  - Playwright Headless Browser        |               |  - Application Drafts & Form Mapping  |
            +-------------------+-------------------+               +-------------------+-------------------+
                                |                                                       |
                                +---------------------------+---------------------------+
                                                            |
                                                            v
                                            +-------------------------------+
                                            |   Cơ sở Dữ liệu Cục bộ (DB)   |
                                            |   - SQLite (careerviet.sqlite3)
                                            |   - SHA-256 Content Validation|
                                            +-------------------------------+
```

### 📚 Tài liệu Giải thích Chuyên sâu Từng Phân hệ (Deep-dive Modules)
Để tìm hiểu sâu về mã nguồn và cách vận hành kỹ thuật chi tiết của từng bộ phận:
- 🌐 [Ingestion & Web Crawlers](internals/ingestion_vi.md) — Cơ chế hoạt động của Adapter, headless Playwright và băm định danh.
- 👤 [Profile & Grounded Evidence](internals/profile_vi.md) — Mô hình bằng chứng nguyên tử, tính bất biến và xác thực sự thật.
- 🎯 [Triage & Evaluation](internals/evaluation_vi.md) — Trích xuất gạch đầu dòng tự động, screening offline và giao thức AI Agent an toàn.
- 📄 [CV Tailoring & PDF Render](internals/cv_render_vi.md) — Quản lý Claims, cổng phê duyệt chống giả mạo và ReportLab engine.
- 📊 [Application Tracking](internals/tracking_vi.md) — State machine tuyến tính, ảnh chụp snapshot bất biến và bảo vệ human-in-the-loop.

---

## 3. Quy trình Vận hành Chuẩn (End-to-End Workflow)

Quy trình 5 bước từ lúc thấy JD đến khi nộp đơn:

```
[1. Thu thập JD]  ==>  [2. Triage Fit]  ==>  [3. May đo CV]  ==>  [4. Tạo Draft Đơn]  ==>  [5. Tracking]
  /crawl URL            /triage <id>          /tailor <id>          /draft create           /track ready
```

### Bước 1: Nạp JD tự động từ URL (`Ingestion`)
Hệ thống sử dụng các adapter chuyên biệt, tự động phát hiện cấu trúc và fallback sang Playwright khi web dùng client-side rendering (React/SPA) hoặc Cloudflare.

- **Slash command:** `/crawl <URL>`
- **CLI:**
  ```bash
  uv run mocnghe jobs crawl "https://itviec.com/it-jobs/..."
  # Thêm --browser nếu trang yêu cầu render JavaScript
  uv run mocnghe jobs crawl "https://indeed.com/viewjob?jk=..." --browser
  ```

### Bước 2: Nạp hồ sơ và Đánh giá độ phù hợp (`Triage`)
Đối chiếu các yêu cầu từ JD (được tự động trích xuất theo gạch đầu dòng) với bằng chứng năng lực thực tế trong `profile.json`.

- **Slash command:**
  - Nạp hồ sơ: `/onboard`
  - Đánh giá: `/triage <job_id>`
- **CLI:**
  ```bash
  uv run mocnghe profile confirm-file
  uv run mocnghe evaluate triage <job_id>
  ```
- **Kết quả trả về:**
  - `practical_fit`: Đủ điều kiện và có dẫn chứng khớp.
  - `evaluate_with_unknowns`: Thiếu một số thông tin (cần người xác nhận thêm).
  - `not_fit`: Vi phạm tiêu chuẩn cứng (địa điểm, loại hợp đồng, lương sàn).

### Bước 3: May đo và Xuất bản CV (`CV Tailoring & PDF Export`)
Tạo một bản sửa đổi CV gắn với mã định danh của JD, trích xuất dẫn chứng phù hợp và xuất file PDF chuẩn in ấn:

- **Slash command:** `/tailor <job_id>`
- **CLI:**
  ```bash
  # 1. Khởi tạo bản thảo CV với các trường danh tính và bằng chứng
  uv run mocnghe cv create --profile-version 1.0 --language en --job-id <job_id> \
    --identity full_name --identity email --identity linkedin \
    --evidence ev_edu --evidence ev_exp_web --evidence ev_skills_db

  # 2. Xem nội dung và lấy hash phê duyệt
  uv run mocnghe cv review <cv_id>

  # 3. Phê duyệt (Approve) và xuất PDF
  uv run mocnghe cv approve <cv_id> --hash <content_hash>
  uv run mocnghe cv export <cv_id> --output cv_output.pdf --max-pages 2
  ```

### Bước 4: Tạo bản nháp nộp đơn (`Application Draft`)
Ánh xạ các câu hỏi tuyển dụng (form application của Greenhouse, Indeed) với các bằng chứng đã được phê duyệt trong CV:

- **CLI:**
  ```bash
  uv run mocnghe draft create <cv_id> --job-id <job_id> \
    --subject "Application for Software Engineer" \
    --route "https://job-boards.eu.greenhouse.io/..." \
    --questions questions.json

  uv run mocnghe draft review <draft_id>
  uv run mocnghe draft approve <draft_id> --hash <content_hash>
  uv run mocnghe draft export <draft_id> --output application_bundle/
  ```

### Bước 5: Quản lý vòng đời ứng tuyển (`Tracking`)
Theo dõi trạng thái chặt chẽ theo state machine tuyến tính:
`discovered` ➔ `shortlisted` ➔ `drafting` ➔ `ready` ➔ `applied` ➔ `interviewing` ➔ `offer`/`rejected`.

- **Slash command:** `/track <job_id> <state>`
- **CLI:**
  ```bash
  # Chuyển trạng thái sang ready (sẵn sàng nộp)
  uv run mocnghe track <job_id> --state ready --cv <cv_id>

  # Sau khi người dùng đã tự tay nộp đơn trên web ATS, ghi nhận lại:
  uv run mocnghe apply <job_id> --cv <cv_id> --confirm
  ```

---

## 4. Cấu trúc Thư mục Dự án

```
mocnghe/
├── src/mocnghe/
│   ├── ingestion/             # Thu thập dữ liệu việc làm
│   │   ├── adapters/          # Hệ thống adapter từng trang web
│   │   │   ├── base.py        # BaseJobAdapter (interface chuẩn)
│   │   │   ├── greenhouse.py  # Adapter cho Greenhouse ATS
│   │   │   ├── itviec.py      # Adapter cho ITviec
│   │   │   ├── indeed.py      # Adapter cho Indeed (JSON-LD / state)
│   │   │   ├── generic.py     # Fallback cho web bất kỳ
│   │   │   ├── browser.py     # Playwright headless runner
│   │   │   └── registry.py    # Router tự động nhận diện URL
│   │   ├── manual.py          # Parser file/stdin truyền thống
│   │   └── results.py         # Schema trạng thái kết quả
│   ├── models/                # Schema Pydantic dữ liệu cốt lõi
│   │   ├── job.py             # Mô hình Job, Salary, Provenance
│   │   ├── profile.py         # CandidateProfile, Evidence, Facts
│   │   └── cv.py              # Claim, CV Revision, Validation
│   ├── storage/
│   │   └── repository.py      # SQLite repository + content hash
│   ├── cv_render.py           # Bộ render PDF chuẩn A4 (ReportLab)
│   ├── evaluation_runtime.py  # Trích xuất yêu cầu & Triage logic
│   └── cli.py                 # Điểm vào dòng lệnh Typer CLI
│
├── .agents/skills/mocnghe/    # Skill dành cho AI Agents (OpenCode, Claude Code)
├── .cursor/rules/             # Rule cho Cursor IDE
├── tests/                     # 130+ unit & integration tests
└── pyproject.toml             # Quản lý dependencies (uv)
```

---

## 5. Hướng Dẫn Tích Hợp Cho Các AI Agent Khác

Nếu bạn muốn trang bị Mốc Nghề cho một Agent mới (như Claude Code, OpenCode, hay Codex):

1. **Thêm skill vào agent:**
   - Trỏ đường dẫn context của agent vào `.agents/skills/mocnghe/SKILL.md`.
2. **Khả năng tương tác:**
   - Agent chỉ cần có quyền chạy lệnh terminal (`uv run mocnghe ...`).
   - Mọi output từ CLI đều xuất ra text hoặc JSON chuẩn, giúp Agent dễ dàng đọc và ra quyết định bước tiếp theo.
3. **Headless Browser Crawler:**
   - Để kích hoạt tính năng crawl web phức tạp, chỉ cần cài thêm dependencies:
     ```bash
     uv pip install -e ".[browser]"
     uv run playwright install chromium
     ```
