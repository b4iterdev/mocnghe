# 🚀 Hướng Dẫn Thiết Lập 1 Chạm Cùng AI Agent (One-Shot Onboarding)

Bạn không cần phải tự cấu hình môi trường hay gõ từng câu lệnh phức tạp. Chỉ cần **copy đoạn prompt bên dưới** và **dán vào AI Agent của bạn** (Hermes, Claude Code, Cursor, OpenCode, Codex, v.v.), Agent sẽ tự động lo toàn bộ phần kỹ thuật.

---

## 📋 Copy & Paste Prompt Này Vào Agent Của Bạn

```markdown
Bạn là trợ lý thiết lập Mốc Nghề (mocnghe). Hãy giúp tôi thiết lập toàn bộ hệ thống từ đầu:

1. KIỂM TRA & CÀI ĐẶT MÔI TRƯỜNG:
   - Kiểm tra Python (>=3.12) và uv. Nếu chưa có thư viện, hãy chạy: `uv sync`
   - Cài đặt tính năng render & browser crawler: `uv pip install -e ".[browser]" && uv run playwright install chromium`
   - Khởi tạo không gian làm việc cục bộ: `uv run mocnghe --workspace data init`

2. THIẾT LẬP HỒ SƠ ỨNG VIÊN (EVIDENCE PROFILE):
   - Hãy hỏi tôi xem tôi đã có sẵn file CV (PDF hoặc văn bản) chưa.
   - NẾU TÔI ĐÃ CÓ CV: Hãy đọc tệp CV của tôi, tự động bóc tách thành danh sách CandidateEvidence chuẩn schema Pydantic (identity, experience, education, skills, credentials, projects). Tuyệt đối không bịa đặt số liệu không có trong CV gốc.
   - NẾU TÔI CHƯA CÓ CV: Hãy phỏng vấn tôi từng câu một (chỉ 1 câu mỗi lượt) về mục tiêu nghề nghiệp, học vấn, kinh nghiệm, kỹ năng và mức lương kỳ vọng.
   - Tạo file `data/profile.json` (version: "1.0").
   - Chạy kiểm tra tính hợp lệ: `uv run mocnghe --workspace data profile validation`
   - Xác nhận và khóa bất biến vào SQLite: `uv run mocnghe --workspace data profile confirm-file`

3. XÁC MINH & BÀN GIAO:
   - Chạy kiểm tra chẩn đoán hệ thống: `uv run mocnghe --workspace data doctor`
   - Khi hoàn tất, báo cáo ngắn gọn cho tôi: hệ thống đã sẵn sàng và hướng dẫn tôi gửi link JD đầu tiên để bắt đầu tìm việc.
```

---

## 💡 Hướng Dẫn Sử Dụng Theo Từng Công Cụ

### 1. Dùng trên Hermes Agent
- Mở cuộc trò chuyện mới trong Hermes Desktop.
- Dán đoạn prompt trên.
- Nếu bạn đã có file CV, đính kèm file hoặc gõ: `CV của tôi nằm ở /đường_dẫn/cv.pdf`.

### 2. Dùng trên Claude Code / OpenCode
- Mở terminal trong thư mục `mocnghe`:
  ```bash
  claude  # hoặc opencode
  ```
- Dán đoạn prompt trên và nhấn Enter.

### 3. Dùng trên Cursor IDE / Windsurf
- Mở Cursor Chat (`Cmd + L` hoặc `Ctrl + L`).
- Chuyển sang chế độ **Agent** (chế độ có quyền chạy terminal).
- Dán đoạn prompt trên và xác nhận các lệnh chạy terminal.

---

## ❓ Những Điều Cần Chuẩn Bị Trước Khi Chạy
1. **Python:** Phiên bản `>= 3.12` ([Tải Python](https://www.python.org/downloads/)).
2. **uv:** Trình quản lý gói siêu tốc của Astral ([Tải uv](https://docs.astral.sh/uv/)):
   ```bash
   # macOS / Linux
   curl -LsSf https://astral.sh/uv/install.sh | sh
   # Windows
   powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
   ```
3. **File CV có sẵn (Tùy chọn):** Nếu có file CV định dạng `.pdf` hoặc `.md`, quá trình thiết lập sẽ hoàn thành chỉ sau 1 phút.
