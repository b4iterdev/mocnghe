# Triage & Evaluation Subsystem (Đánh giá Độ phù hợp & Tách Yêu cầu)

Phân hệ `evaluation` đảm nhiệm việc đối chiếu giữa yêu cầu của nhà tuyển dụng và năng lực của ứng viên. Phân hệ này bao gồm hai tầng: **Triage cục bộ (deterministic)** và **Evaluation Packet xuất cho AI Agent/LLM**.

---

## 1. Trích xuất Yêu cầu Cấu trúc (`_requirements_from_job`)

Thay vì gửi cả JD thô vào mô hình ngôn ngữ lớn (tốn kém và dễ gây ảo giác), Mốc Nghề triển khai bộ parser dòng lệnh xác định (`evaluation_runtime.py`):

1. **Nhận diện Vùng Tiêu đề:**
   - **Bắt buộc (`required`):** `required qualifications`, `must have`, `yêu cầu`, `kỹ năng yêu cầu`...
   - **Ưu tiên (`preferred`):** `good to have`, `nice to have`, `preferred`, `ưu tiên`, `bonus`...
   - **Vùng Dừng (`stop`):** `benefits`, `what we offer`, `phúc lợi`, `quyền lợi`...
2. **Bóc tách Gạch đầu dòng (`_is_bullet`):**
   - Tự động nhận diện các ký tự đánh dấu: `-`, `•`, `*`, `·`, `▪`, `▸`.
   - Gán tuần tự mã định danh: `req_001`, `req_002`, `req_003`...
   - Lưu trạng thái: `required_status: "required" | "preferred"`.

---

## 2. Công cụ Đánh giá Sơ bộ Triage (`triage.py`)

Thực hiện đánh giá tức thì không cần mạng Internet hay API key của nhà cung cấp LLM:

```
[ Hồ sơ Xác nhận ] + [ Tin tuyển dụng ]
                 |
                 v
        triage_job(profile, job)
                 |
                 +---> Kiểm tra Tiêu chí Cứng (Hard Constraints):
                 |       - Lương sàn: profile.preferences.compensation_floor
                 |       - Ngành cấm: industry_exclusions
                 |       - Giấy phép hành nghề bắt buộc (Y tá, tài xế xe nâng...)
                 |
                 +---> Kiểm tra Vùng Không rõ (Unknowns):
                 |       - Hình thức làm việc chưa phân loại (intern vs fulltime)
                 |       - Địa điểm làm việc chưa rõ ràng
                 |
                 v
        Kết luận (Verdict):
          * practical_fit: Thỏa mãn toàn bộ, không có vi phạm
          * evaluate_with_unknowns: Đạt điều kiện nhưng cần xác nhận thêm
          * not_fit: Vi phạm điều kiện cứng
```

---

## 3. Giao thức Đánh giá bằng AI Agent (`EvaluationPacket`)

Khi cần Agent tham gia phân tích sâu, Mốc Nghề bảo vệ quyền riêng tư và chống prompt injection thông qua hợp đồng dữ liệu nghiêm ngặt:

### 3.1. Đóng gói Gói Đánh giá (`export-packet`)
- **Tẩy bỏ Thông tin Danh tính:** Mọi trường `identity` (họ tên, email, số điện thoại, URL mạng xã hội) và các bằng chứng có cờ `provenance == "identity"` bị loại bỏ hoàn toàn trước khi xuất file.
- **Khóa Băm Nội dung:** Gói ghi nhận `profile_content_hash` và `jd_content_hash`.

### 3.2. Kiểm định Báo cáo Trả về (`import-report`)
Khi nhận JSON phản hồi từ Agent/LLM, hệ thống chạy hàm `validate_evaluation_response`:
1. **Khớp ID:** Phải đánh giá chính xác từng `req_xxx` theo thứ tự nguyên bản, không được bỏ sót hay tự thêm bớt.
2. **Khớp Trích dẫn Bằng chứng:** Nếu đánh giá là `status: "supported"`, phải trích dẫn đúng nguyên văn `source_quote` có sẵn trong gói.
3. **Kiểm tra Giao thoa Từ vựng (`_has_conservative_overlap`):** Trích dẫn được đưa ra phải có sự giao thoa từ khóa thực chất với câu văn của yêu cầu, ngăn chặn tình trạng Agent trích dẫn bừa một bằng chứng không liên quan.
