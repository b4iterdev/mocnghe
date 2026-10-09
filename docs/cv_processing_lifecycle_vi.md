# Quy trình Xử lý Hồ sơ: Từ Tệp CV đến Bản CV May đo Hoàn chỉnh

Tài liệu này giải thích chi tiết cơ chế hoạt động bên trong của hệ thống khi người dùng đưa tệp CV vào: hệ thống thực hiện những tác vụ gì, dữ liệu chuyển đổi ra sao qua từng bước, và các cơ chế an toàn nào được kích hoạt.

---

## 1. Sơ đồ Tổng quan Luồng Xử lý CV

```
[ Người dùng cung cấp CV ] (PDF / DOCX / Text)
            |
            v
[ BƯỚC 1: Trích xuất & Phân rã Sự thật (Evidence Extraction) ]
   - Đọc văn bản thô (PdfReader / text extraction)
   - Bóc tách thành các bằng chứng nguyên tử (CandidateEvidence)
   - Lưu trữ source_quote nguyên văn làm mốc bảo chứng
            |
            v
[ BƯỚC 2: Cấu trúc hóa Hồ sơ (Profile Standardization) ]
   - Gom các bằng chứng vào tệp `profile.json`
   - Liên kết các sự thật bắt buộc (FactRequirement -> evidence_ids)
   - Gán mức độ tin cậy (uncertainty: low/medium, status: document_verified)
            |
            v
[ BƯỚC 3: Xác thực Khế ước & Đóng băng Bất biến (Confirmation Gate) ]
   - Lệnh: `mocnghe profile confirm-file`
   - Kiểm định chéo: mọi fact phải trỏ về evidence có thật
   - Đóng dấu thời gian confirmed_at (UTC)
   - Tính mã băm SHA-256 (profile_content_hash)
   - Ghi vào bảng `profiles` trong SQLite (Bất biến, không thể sửa đổi)
            |
            v
[ BƯỚC 4: May đo theo Tin Tuyển dụng Cụ thể (CV Tailoring) ]
   - Lệnh: `mocnghe cv create --job-id <id> --evidence <ev1> --evidence <ev2>...`
   - Tạo danh sách các khẳng định (Claims) gắn chặt với `job_id` và `profile_version`
   - Hai chế độ:
       * extractive: text giữ nguyên văn source_quote
       * proposed: câu từ được trau chuốt/dịch thuật (gắn cờ chờ duyệt)
            |
            v
[ BƯỚC 5: Cổng Phê duyệt Chống Giả mạo (Cryptographic Approval Gate) ]
   - Lệnh: `mocnghe cv review <cv_id>` -> lấy mã `content_hash`
   - Lệnh: `mocnghe cv approve <cv_id> --hash <content_hash>`
   - Bất kỳ thay đổi nào làm lệch hash sẽ tự động hủy phê duyệt
            |
            v
[ BƯỚC 6: Kết xuất Bản in PDF Chuẩn A4 (ReportLab Rendering) ]
   - Lệnh: `mocnghe cv export <cv_id> --output cv.pdf --max-pages 2`
   - Escape toàn bộ ký tự chống lỗi/mã độc ReportLab
   - Kiểm tra giới hạn số trang nghiêm ngặt (chống tràn trang lẻ)
   - Xuất gói bundle: `cv.pdf` (cho NTD) + `cv.json` (cho ATS/Audit)
```

---

## 2. Chi tiết Từng Bước

### Bước 1: Trích xuất Văn bản & Phân rã Dẫn chứng (Evidence Extraction)
- **Hành động:** Khi tiếp nhận CV (ví dụ `cv-nguyen-minh-thai.pdf`), hệ thống hoặc AI Agent trích xuất văn bản thô.
- **Biến đổi dữ liệu:** Văn bản dài được phân rã thành các mẩu thông tin nguyên tử gọi là `CandidateEvidence`. Mỗi mẩu ghi lại:
  - `evidence_id`: Mã định danh duy nhất (ví dụ: `ev_exp_steam_camera`).
  - `source_quote`: Đoạn văn bản trích dẫn nguyên văn từ CV gốc. Đây là **mốc đối chiếu bắt buộc** để ngăn AI bịa đặt kinh nghiệm.
  - `status`: Gán trạng thái xác minh (ví dụ: `document_verified`).

### Bước 2: Chuẩn hóa Hồ sơ (`profile.json`)
- **Hành động:** Các bằng chứng được cấu trúc hóa theo lược đồ Pydantic `CandidateProfile`.
- **Ràng buộc an toàn:** Thiết lập các `FactRequirement`. Ví dụ, nếu khẳng định ứng viên là *"Sinh viên ngành CNTT"*, trường này bắt buộc phải liệt kê `evidence_ids: ["ev_edu_phenikaa"]`.

### Bước 3: Xác thực & Đóng băng Bất biến (`profile confirm-file`)
- **Hành động:** Chạy lệnh:
  ```bash
  uv run mocnghe profile confirm-file
  ```
- **Hệ thống làm gì ngầm bên dưới:**
  1. Kiểm tra JSON Decode và Pydantic schema validation.
  2. Xác minh tính toàn vẹn: Không cho phép duplicate `evidence_id`, từ chối lưu nếu có fact trỏ tới `evidence_id` không tồn tại.
  3. Gán thời gian xác nhận chuẩn UTC (`confirmed_at = datetime.now(UTC)`).
  4. Tính toán mã băm SHA-256 trên toàn bộ dữ liệu.
  5. Ghi vào bảng `profiles` trong database SQLite (`careerviet.sqlite3`).
  - **Đặc tính:** Phiên bản hồ sơ này trở thành **bất biến (immutable)**. Không ai có thể sửa đè lên bản ghi này mà không tăng số version.

### Bước 4: May đo CV theo Tin tuyển dụng (`cv create` & `cv revise`)
- **Hành động:** Người dùng hoặc Agent chọn lọc các bằng chứng phù hợp nhất với JD mục tiêu:
  ```bash
  uv run mocnghe cv create --profile-version 1.0 --language en --job-id job_123 \
    --identity full_name --identity email --identity linkedin \
    --evidence ev_edu --evidence ev_exp_steam_camera --evidence ev_skills_backend
  ```
- **Hệ thống làm gì ngầm bên dưới:**
  - Khởi tạo bản ghi trong bảng `cv_revisions`.
  - Chuyển đổi các bằng chứng thành các khẳng định (`Claim`).
  - Nếu câu chữ được viết lại cho mượt hơn hoặc dịch sang tiếng Anh, câu đó mang trạng thái `mode: "proposed"`. Hệ thống gắn cảnh báo: *Nội dung đề xuất cần con người kiểm tra, không được tự động coi là sự thật.*

### Bước 5: Cổng Phê duyệt Chống Giả mạo (`cv approve`)
- **Hành động:** Người dùng rà soát nội dung và phê duyệt:
  ```bash
  uv run mocnghe cv review <cv_id>   # In ra nội dung và content_hash
  uv run mocnghe cv approve <cv_id> --hash <content_hash>
  ```
- **Hệ thống làm gì ngầm bên dưới:**
  - Tính toán mã băm `digest(cv)` độc lập.
  - So khớp với mã băm do người dùng nhập vào. Nếu khớp 100%, ghi nhận vào bảng `cv_approvals`.
  - Nếu bất kỳ ký tự nào trong database bị sửa đổi trái phép sau đó, mã băm sẽ lệch và trạng thái phê duyệt lập tức bị hủy bỏ.

### Bước 6: Kết xuất Bản in PDF Chuẩn A4 (`cv export`)
- **Hành động:** Xuất bản tài liệu:
  ```bash
  uv run mocnghe cv export <cv_id> --output cv_final.pdf --max-pages 2
  ```
- **Hệ thống làm gì ngầm bên dưới:**
  1. Kiểm tra `svc.approved(cv_id)`: Nếu CV chưa được phê duyệt qua cổng hash, lệnh ném lỗi từ chối ngay lập tức.
  2. Mã hóa an toàn văn bản (XML escape) để ngăn ngừa lỗi render.
  3. Đo đạc bố cục trang ReportLab. Nếu nội dung vượt quá `--max-pages` (ví dụ dài sang trang 3), engine lập tức dừng lại với lỗi `CV exceeds page budget`, yêu cầu tóm tắt gọn gàng thay vì xuất ra bản in lỗi.
  4. Tạo ra file PDF hoàn chỉnh và tệp metadata `cv.json` đi kèm.
