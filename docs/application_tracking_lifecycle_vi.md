# Luồng Đánh Giá, Tinh Chỉnh & Nộp Đơn Ứng Tuyển

Tài liệu này giải thích chi tiết quy trình khép kín từ khi ứng viên có một tin tuyển dụng (JD) trong cơ sở dữ liệu cho đến khi tạo đơn xin việc, may đo CV, chuyển trạng thái qua các bước kiểm soát, và ghi nhận kết quả nộp đơn thủ công an toàn.

---

## 1. Sơ đồ Luồng Đánh Giá & Theo Dõi Ứng Tuyển

```
[ Tin Tuyển Dụng Đã Lưu ] + [ Hồ Sơ Ứng Viên Đã Duyệt ]
            |
            v
[ BƯỚC 1: Đánh Giá Sơ Bộ Không Cần LLM (Local Triage) ]
   - Lệnh: `mocnghe evaluate triage <job_id>`
   - Bóc tách yêu cầu: _requirements_from_job tách các gạch đầu dòng
   - Đối chiếu quy tắc:
       * Vi phạm lương sàn / ngành nghề cấm -> `not_fit`
       * Thiếu thông tin hình thức làm việc -> `evaluate_with_unknowns`
       * Đạt toàn bộ tiêu chí -> `practical_fit`
            |
            v
[ BƯỚC 2: Khởi Tạo Hồ Sơ Ứng Tuyển Trong Pipeline (Shortlisting) ]
   - Lệnh: `mocnghe track <job_id> --state shortlisted`
   - Ghi nhận vào bảng `applications`
   - Ghi nhật ký sự kiện `application_events` (từ discovered -> shortlisted)
            |
            v
[ BƯỚC 3: Tạo Bản Nháp Ứng Tuyển (Drafting) ]
   - Lệnh: `mocnghe track <job_id> --state drafting`
   - May đo CV:
       * `mocnghe cv create` -> `mocnghe cv revise` -> `mocnghe cv approve`
   - Ánh xạ câu hỏi tuyển dụng (Form Application):
       * `mocnghe draft create <cv_id> --questions questions.json`
       * Cột mốc câu trả lời bắt buộc phải trỏ vào bằng chứng trong CV đã duyệt
            |
            v
[ BƯỚC 4: Khóa Đóng Gói Sẵn Sàng (Ready State & Audit Snapshot) ]
   - Lệnh: `mocnghe track <job_id> --state ready --cv <cv_id>`
   - Kiểm tra: Bắt buộc CV phải ở trạng thái đã duyệt (`approved == True`)
   - Chụp ảnh snapshot bất biến (`submission_json`):
       * Gói CV hoàn chỉnh + Hash của JD + Phiên bản hồ sơ gốc
   - Tính toán mã băm kiểm toán: `submission_hash = SHA-256(snapshot)`
            |
            v
[ BƯỚC 5: Nộp Đơn Thủ Công & Ghi Nhận Xác Nhận (Apply Gate) ]
   - Con người tự tay nộp hồ sơ trên website tuyển dụng (Greenhouse, Lever...)
   - Ghi nhận có chủ đích:
       `mocnghe apply <job_id> --cv <cv_id> --confirm`
   - Hệ thống đánh dấu: `applied = True`, lưu thời điểm `applied_at` (UTC)
   - Tiếp tục theo dõi: `interviewing` -> `offer` / `rejected`
```

---

## 2. Chi tiết Từng Bước

### Bước 1: Đánh Giá Sơ Bộ Triage
- Hệ thống chạy hàm `triage_job(profile, job)` độc lập trên máy cục bộ.
- Hoàn toàn không tốn chi phí token AI và không gửi dữ liệu ra ngoài.
- Giúp người tìm việc loại bỏ nhanh chóng các công việc trái ngành hoặc dưới mức lương kỳ vọng.

### Bước 2 & 3: Đưa Vào Danh Sách & Soạn Thảo (Shortlisted & Drafting)
- Trạng thái chuyển dịch tuần tự: `discovered` ➔ `shortlisted` ➔ `drafting`.
- **May đo CV:** Lựa chọn đúng những bằng chứng (kinh nghiệm, dự án) có liên quan trực tiếp đến các gạch đầu dòng yêu cầu của JD.
- **Tạo Đơn Nháp (`draft`):** Ánh xạ các câu hỏi trong mẫu đơn (ví dụ: *"Bạn có bao nhiêu năm kinh nghiệm SQL?"*) với chính các dẫn chứng đã được duyệt trong CV. Ngăn ngừa tình trạng câu trả lời trên form mẫu mâu thuẫn với nội dung viết trong CV.

### Bước 4: Chốt Khóa Sẵn Sàng (`ready`)
- Lệnh: `mocnghe track <job_id> --state ready --cv <cv_id>`.
- **Cơ chế an toàn:** Nếu CV chưa được phê duyệt qua cổng mã băm (`cv approve`), hệ thống sẽ từ chối chuyển trạng thái sang `ready`.
- **Ảnh chụp Kiểm toán (`submission_json`):** Hệ thống tạo một bản ghi đóng băng toàn bộ nội dung CV, JD và Profile tại thời điểm đó, tính mã `submission_hash`. Nhờ vậy, ngay cả 6 tháng sau xem lại, ứng viên vẫn biết chính xác 100% tài liệu mình đã chuẩn bị cho công ty đó là gì.

### Bước 5: Xác Nhận Nộp Đơn (`apply`)
- **Nguyên tắc cốt lõi:** Mốc Nghề **không tự động gửi đơn hay spam nhà tuyển dụng**.
- Sau khi ứng viên tự tay nộp CV trên website công ty, ứng viên chạy lệnh:
  ```bash
  uv run mocnghe apply <job_id> --cv <cv_id> --confirm
  ```
- Đây là bước chốt chặn cuối cùng bảo đảm mọi đơn nộp đều do con người kiểm soát.
