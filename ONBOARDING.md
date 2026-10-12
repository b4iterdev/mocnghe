# 🚀 Thiết Lập Mốc Nghề 1 Dòng Lệnh (Zero-Download Onboarding)

Người dùng **không cần tải trước mã nguồn (không cần clone repo)**. Chỉ cần mở bất kỳ AI Agent nào (Hermes, Claude Code, Cursor, Windsurf, OpenCode, Codex) và gửi duy nhất 1 câu:

> 💬 **"Đọc https://raw.githubusercontent.com/b4iterdev/mocnghe/main/ONBOARDING.md và thiết lập mocnghe cho tôi"**  
> *(hoặc: "Đọc https://github.com/b4iterdev/mocnghe và thiết lập mocnghe cho tôi")*

---

## 🤖 HƯỚNG DẪN DÀNH CHO AI AGENT (AGENT INSTRUCTIONS)

Khi bạn (AI Agent) nhận được yêu cầu cài đặt hoặc đọc tệp này từ người dùng, hãy thực hiện tuần tự các bước sau trên máy tính của người dùng:

### BƯỚC 1: Cài đặt công cụ CLI toàn cục (Không cần clone repo)
Kiểm tra xem hệ thống đã có `uv` chưa. Nếu chưa có, hướng dẫn hoặc cài đặt `uv`.
Sau đó chạy lệnh cài đặt Mốc Nghề trực tiếp từ GitHub vào hệ thống:
```bash
uv tool install --force "mocnghe[browser] @ git+https://github.com/b4iterdev/mocnghe.git"
uv run playwright install chromium
```
*(Lưu ý: Nếu người dùng yêu cầu rõ là muốn clone mã nguồn để phát triển, hãy chạy `git clone https://github.com/b4iterdev/mocnghe.git && cd mocnghe && uv sync` thay thế).*

### BƯỚC 2: Khởi tạo Không gian làm việc
Tạo một thư mục làm việc (hoặc dùng thư mục hiện tại) và khởi tạo CSDL:
```bash
mocnghe --workspace data init
```

### BƯỚC 3: Cài đặt Skill cho Agent (Tùy nền tảng)
- **Nếu đang chạy trên Hermes Agent:** Tải skill vào `~/.hermes/skills/productivity/mocnghe/SKILL.md`:
  ```bash
  mkdir -p ~/.hermes/skills/productivity/mocnghe
  curl -fsSL https://raw.githubusercontent.com/b4iterdev/mocnghe/main/.agents/skills/mocnghe/SKILL.md -o ~/.hermes/skills/productivity/mocnghe/SKILL.md
  ```
- **Nếu đang chạy trên Cursor / Windsurf:** Tải quy tắc vào `.cursor/rules/mocnghe.md`:
  ```bash
  mkdir -p .cursor/rules
  curl -fsSL https://raw.githubusercontent.com/b4iterdev/mocnghe/main/.cursor/rules/mocnghe.md -o .cursor/rules/mocnghe.md
  ```
- **Nếu đang chạy trên Claude Code / OpenCode / Codex:** Tải skill vào `.agents/skills/mocnghe/SKILL.md`:
  ```bash
  mkdir -p .agents/skills/mocnghe
  curl -fsSL https://raw.githubusercontent.com/b4iterdev/mocnghe/main/.agents/skills/mocnghe/SKILL.md -o .agents/skills/mocnghe/SKILL.md
  ```

### BƯỚC 4: Thiết lập Hồ sơ Ứng viên (Profile Onboarding)
1. Hỏi người dùng: **"Bạn đã có sẵn file CV (PDF hoặc văn bản) chưa?"**
2. **Trường hợp 1 (Đã có CV):** Yêu cầu người dùng cung cấp đường dẫn hoặc gửi file CV. Đọc tệp và tự động trích xuất các thông tin:
   - `identity`: name, email, phone, linkedin, github, location.
   - `evidence`: Bóc tách từng kinh nghiệm, dự án, học vấn, kỹ năng thành các mục nguyên tử có `id` (ví dụ `ev_exp_1`, `ev_edu_1`), trích dẫn nguyên văn `quote`. Tuyệt đối không tự bịa đặt số liệu.
   - Ghi vào tệp `data/profile.json` (version: `"1.0"`).
3. **Trường hợp 2 (Chưa có CV):** Phỏng vấn người dùng từng câu một (chỉ 1 câu mỗi lượt) về mục tiêu nghề nghiệp, học vấn, kinh nghiệm, kỹ năng, lương kỳ vọng; sau đó ghi vào `data/profile.json`.
4. Xác thực và lưu trữ bất biến:
   ```bash
   mocnghe --workspace data profile validation
   mocnghe --workspace data profile confirm-file
   ```

### BƯỚC 5: Kiểm tra sức khỏe hệ thống & Bàn giao
Chạy kiểm tra chẩn đoán:
```bash
mocnghe --workspace data doctor
```
Thông báo cho người dùng biết hệ thống Mốc Nghề đã được cài đặt hoàn tất và hướng dẫn người dùng dán link JD đầu tiên (hoặc gõ `/mocnghe-crawl <url>`) để bắt đầu tìm việc.

---

## 📋 Prompt Dự Phòng (Dành cho Agent không tự mở URL được)

Nếu AI Agent của bạn không có tính năng duyệt web để tự đọc link trên, hãy copy trực tiếp toàn bộ khối nội dung dưới đây và gửi cho Agent:

```markdown
Bạn là trợ lý thiết lập Mốc Nghề (mocnghe). Hãy cài đặt và thiết lập cho tôi:
1. Chạy lệnh cài đặt CLI toàn cục trực tiếp từ GitHub:
   uv tool install --force "mocnghe[browser] @ git+https://github.com/b4iterdev/mocnghe.git"
   uv run playwright install chromium
2. Khởi tạo workspace: `mocnghe --workspace data init`
3. Hỏi tôi đường dẫn file CV của tôi (nếu có) để bóc tách thành data/profile.json hoặc phỏng vấn tôi từng bước.
4. Chạy `mocnghe --workspace data profile validation` và `mocnghe --workspace data profile confirm-file`
5. Kiểm tra chẩn đoán bằng `mocnghe --workspace data doctor` và báo cáo hoàn tất.
```
