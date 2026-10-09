# CV Tailoring & Rendering Subsystem (May đo & Kết xuất CV)

Phân hệ `cv` và `cv_render` quản lý việc tuyển chọn bằng chứng, tinh chỉnh văn phong phù hợp với từng JD cụ thể, và kết xuất ra tài liệu PDF chuẩn in ấn A4.

---

## 1. Mô hình Khẳng định Năng lực (`Claim` trong `cv.py`)

Một bản CV trong Mốc Nghề không phải là một đoạn văn tự do, mà là một danh sách các khẳng định (`list[Claim]`) có cấu trúc:

```python
class Claim(BaseModel):
    evidence_id: str          # Bắt buộc trỏ về bằng chứng có sẵn
    source_quote: str         # Câu trích dẫn gốc trong bằng chứng
    text: str                 # Câu hiển thị trên CV (có thể dịch hoặc viết lại)
    section: Literal["experience", "education", "skills", "credentials", "other"]
    mode: Literal["extractive", "proposed"]
    uncertainty: str
    status: str
```

### 1.1. Chế độ Extractive vs. Proposed
- **`mode: "extractive"`**: Yêu cầu nghiêm ngặt `text == source_quote`. Giữ nguyên văn trích dẫn gốc từ CV/hồ sơ ban đầu, không thay đổi dù chỉ một ký tự.
- **`mode: "proposed"`**: Cho phép thay đổi văn phong hoặc dịch ngôn ngữ (`EN` sang `VI` hoặc ngược lại). Tuy nhiên, nội dung này được đánh dấu rõ ràng là *đề xuất* và bắt buộc ứng viên phải rà soát xác nhận.

### 1.2. Chuẩn hóa Tự động (`@field_validator`)
Hệ thống tự động map các từ ngữ thông dụng sang enum chuẩn để tránh lỗi người dùng:
- `summary`, `objective`, `projects` ➔ map sang `other`.
- `certifications`, `licenses` ➔ map sang `credentials`.
- `rewrite`, `tailored`, `translated` ➔ map sang `proposed`.

---

## 2. Quy trình Phê duyệt Chống Giả mạo (Approval Gate)

Mốc Nghề áp dụng cơ chế xác thực hai bước:

```
[ cv create / revise ]
          |
          v
  Sinh ra bản thảo CV
          |
          v
[ cv review <cv_id> ]  --->  Tính toán content_hash = SHA-256(CV payload)
          |
          v
[ cv approve <cv_id> --hash <content_hash> ]
          |
          v
  Ghi nhận vào bảng `cv_approvals` (chỉ khi hash nhập vào khớp tuyệt đối)
          |
          v
[ cv export <cv_id> ]  --->  Kiểm tra: Nếu chưa approved -> TỪ CHỐI XUẤT PDF
```

> **Nguyên tắc An toàn:** Không ai (kể cả AI Agent) có thể tự ý thay đổi một từ trong CV đã được duyệt mà vẫn giữ nguyên trạng thái phê duyệt. Bất kỳ sửa đổi nhỏ nào cũng làm đổi `content_hash`, tự động hủy trạng thái phê duyệt cũ.

---

## 3. Bộ Kết xuất PDF ReportLab (`cv_render.py`)

1. **Bảo mật Nội dung:** Toàn bộ văn bản của người dùng được escape mã hóa (`xml.sax.saxutils.escape`), loại bỏ nguy cơ chèn mã thực thi hay lỗi thẻ XML khi biên dịch qua ReportLab.
2. **Kiểm soát Kích thước Trang Nghiêm ngặt (`--max-pages`):**
   - Đăng ký hook `check_page(canvas, document)`.
   - Nếu nội dung dài làm tràn số trang cho phép (mặc định tối đa 2 trang), trình render sẽ lập tức dừng và ném lỗi `CV exceeds page budget`, buộc người dùng/agent phải tóm tắt lại thay vì để trang thứ 3 bị rớt 1-2 dòng luộm thuộm.
3. **Đóng gói Bundle:** Lệnh xuất bản tạo ra một thư mục chứa cả `cv.pdf` (cho con người) và `cv.json` (cho máy đọc).
