# User & AI Agent Surface Subsystem (Giao diện Người dùng & AI Agent)

Phân hệ giao diện của Mốc Nghề được thiết kế theo triết lý **Giao diện Kép Đối xứng (Dual-Interface Parity)**: Mọi tính năng mà con người có thể thực hiện thông qua dòng lệnh (`CLI`) thì AI Agent cũng có thể thực hiện thông qua công cụ dòng lệnh hoặc các lệnh tắt (`Slash Commands`), với hành vi và ràng buộc kiểm định hoàn toàn đồng nhất.

---

## 1. Kiến trúc Tổng thể

```
                 +-------------------------------------------------------------+
                 |                       NGƯỜI DÙNG / AGENT                    |
                 +------------------------------+------------------------------+
                                                |
                        +-----------------------+-----------------------+
                        |                                               |
                        v                                               v
        [ Con người thao tác Trực tiếp ]                 [ AI Agent Tự hành ]
        - Terminal Shell (Bash/Zsh)                      - Hermes Agent
        - Script CI/CD hoặc Makefile                     - Cursor / Claude Code / OpenCode
                        |                                               |
                        | (Lệnh CLI tường minh)                         | (Slash Commands / Prompts)
                        |                                               |
                        |       /crawl, /onboard, /triage, /tailor, /track
                        |                               |
                        +---------------+---------------+
                                        |
                                        v
                        +-------------------------------+
                        |       Lớp Điều phối Lệnh      |
                        |   .cursor/rules/mocnghe.md    |
                        |   .agents/skills/mocnghe/     |
                        |   ~/.hermes/skills/mocnghe/   |
                        +---------------+---------------+
                                        |
                                        v
                        +-------------------------------+
                        |       Typer CLI Engine        |
                        |         (src/mocnghe/cli.py)  |
                        +---------------+---------------+
                                        |
         +------------------------------+------------------------------+
         |                              |                              |
         v                              v                              v
  [ jobs Subcommand ]          [ profile Subcommand ]        [ evaluate Subcommand ]
  - crawl / search / ingest    - confirm-file / validation   - triage / export-packet
         |                              |                              |
         +------------------------------+------------------------------+
                                        |
                                        v
                        [ cv / draft / track Subcommands ]
                        - create / revise / approve / export
                        - track / apply
```

---

## 2. Các Thành phần Cốt lõi

### 2.1. Typer CLI Engine (`src/mocnghe/cli.py`)
Mốc Nghề sử dụng thư viện `typer` để xây dựng CLI hiện đại:
- **Phân cấp Lệnh Nhóm (Subcommand Apps):**
  - `jobs_app`: Quản lý tin tuyển dụng (`crawl`, `search`, `ingest`, `list`, `show`).
  - `profile_app`: Quản lý hồ sơ ứng viên (`confirm-file`, `validation`, `answer`, `review`, `correct`, `confirm`).
  - `evaluate_app`: Đánh giá độ phù hợp và xuất/nhập gói đánh giá (`triage`, `export-packet`, `import-report`).
  - `cv_app`: Tạo, sửa đổi, phê duyệt và xuất bản CV PDF (`create`, `revise`, `review`, `approve`, `export`, `export-packet`, `import-response`).
  - `draft_app`: Quản lý đơn xin việc và ánh xạ câu hỏi form (`create`, `review`, `approve`, `export`).
  - `applications_app` & `track` / `apply`: Quản lý tiến trình nộp đơn.
- **Ràng buộc Tham số Nghiêm ngặt:** Các tùy chọn mutually exclusive (như `--file`, `--stdin`, `--url` trong `import-jd`) được kiểm tra chủ động ngay tại hàm CLI để ngăn chặn trạng thái mập mờ.

### 2.2. Lớp Quy tắc Cho AI Agent (Agent Rules & Skills Layer)
Để các Agent như Cursor, Claude Code, hay OpenCode hiểu cách điều khiển CLI mà không cần con người hướng dẫn từng câu lệnh, Mốc Nghề cung cấp các tệp chỉ dẫn ngữ cảnh:
- **`.cursor/rules/mocnghe.md`**: Tự động nạp vào Cursor IDE khi mở workspace. Hướng dẫn Agent ánh xạ các slash command như `/crawl`, `/tailor` thành lệnh `uv run mocnghe ...`.
- **`.agents/skills/mocnghe/SKILL.md`**: Định dạng tiêu chuẩn cho các Agent mã nguồn mở và autonomous coding agents.
- **Hermes Global Skill (`~/.hermes/skills/productivity/mocnghe/`)**: Cho phép Hermes Agent nhận diện slash commands ở cấp độ toàn hệ thống.

---

## 3. Giao thức Tương tác An toàn giữa Agent và CLI

Khi làm việc với các mô hình ngôn ngữ lớn (LLM), Mốc Nghề thiết lập các hàng rào bảo vệ (guardrails) sau:

1. **Dữ liệu Ra Chuẩn hóa (Structured Output):**
   - Hầu hết các lệnh xem xét (`review`, `track`, `validation`) đều in ra định dạng JSON sạch hoặc chuỗi key-value dễ đọc bằng máy. Agent chỉ cần đọc stdout để nhận diện trạng thái tiếp theo.
2. **Không Tin tưởng Dữ liệu Văn bản (Untrusted Text):**
   - Mọi văn bản lấy từ web hoặc từ JD đều được coi là dữ liệu thô, không được thực thi như chỉ dẫn dòng lệnh. Điều này ngăn chặn triệt để tấn công **Indirect Prompt Injection** thông qua nội dung tuyển dụng độc hại.
3. **Cổng Phê duyệt Bắt buộc (Approval Gate):**
   - Agent có thể đề xuất chỉnh sửa CV (`cv revise`) hoặc tạo đơn nháp (`draft create`), nhưng **không thể tự phê duyệt** nếu không cung cấp mã băm SHA-256 chính xác (`--hash <content_hash>`).
   - Agent **không bao giờ được tự ý nộp đơn** (`apply`). Quyền nộp đơn thực tế luôn thuộc về con người.
