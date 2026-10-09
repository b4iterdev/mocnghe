# Application Tracking Subsystem (Theo dõi Vòng đời Đơn Ứng tuyển)

Phân hệ `applications` quản lý trạng thái nộp đơn và lưu trữ ảnh chụp bằng chứng (submission snapshot) theo nguyên tắc bất biến và hoàn toàn nằm dưới quyền kiểm soát của người dùng.

---

## 1. Máy trạng thái Tuyến tính (State Machine)

Trạng thái ứng tuyển tuân thủ quy tắc chuyển tiếp nghiêm ngặt, không cho phép nhảy cóc:

```
[ discovered ] (Phát hiện tin tuyển dụng)
      |
      v
[ shortlisted ] (Đưa vào danh sách ứng tuyển)
      |
      v
[ drafting ] (Đang may đo CV & tạo đơn nháp)
      |
      v
[ ready ] (Đã có CV được phê duyệt, sẵn sàng nộp)
      |
      +---> [ applied ] (Người dùng xác nhận ĐÃ TỰ TAY NỘP ĐƠN)
      |         |
      |         +---> [ interviewing ] (Phỏng vấn)
      |         |         |
      |         |         +---> [ offer ] (Nhận lời mời làm việc)
      |         |         +---> [ rejected ] (Bị từ chối)
      |         |
      |         +---> [ withdrawn ] (Rút đơn)
      |
      +---> [ archived ] (Lưu trữ / Đóng lại)
```

---

## 2. Ảnh chụp Nộp đơn Bất biến (Submission Snapshot)

Khi chuyển trạng thái sang `ready`, hệ thống tự động chụp một bức ảnh snapshot (`submission_json`) bao gồm:
- Bản CV đã được phê duyệt tại đúng thời điểm đó.
- Phiên bản hồ sơ ứng viên gốc.
- Bản tin tuyển dụng mục tiêu (cùng mã băm SHA-256).

Toàn bộ khối snapshot này được tính mã băm `submission_hash`. Nhờ đó, ngay cả khi sau này JD bị xóa khỏi web hay ứng viên cập nhật hồ sơ mới, hệ thống vẫn lưu lại chính xác nguyên trạng những gì đã chuẩn bị nộp cho nhà tuyển dụng.

---

## 3. Nguyên tắc Human-in-the-Loop về Lệnh `apply`

Lệnh `track` chỉ cho phép chuyển tối đa đến trạng thái `ready`.

Để chuyển sang trạng thái `applied`, người dùng bắt buộc phải dùng lệnh chuyên biệt:
```bash
uv run mocnghe apply <job_id> --cv <cv_id> --confirm
```
- **Hệ thống không tự gửi đơn:** Lệnh này KHÔNG thực hiện gửi HTTP POST hay điền form tự động.
- **Ý nghĩa:** Đây là lời xác nhận có ý thức của người dùng: *"Tôi xác nhận rằng tôi đã tự tay gửi bộ hồ sơ này lên website tuyển dụng."*
- Giúp người tìm việc tránh hoàn toàn rủi ro bị AI nộp đơn tự động bừa bãi khi chưa kiểm tra kỹ.
