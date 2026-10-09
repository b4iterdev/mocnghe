# Profile & Evidence Subsystem (Hồ sơ Ứng viên & Bằng chứng Dẫn chứng)

Phân hệ `profile` quản lý thông tin cốt lõi của ứng viên. Triết lý quan trọng nhất của phân hệ này là: **Mọi nhận định, kỹ năng hay kinh nghiệm phải được bảo chứng bằng bằng chứng thực tế (`evidence-grounded`)**, không chấp nhận dữ liệu tự suy diễn hay phóng đại.

---

## 1. Mô hình Dữ liệu Cốt lõi (`models/profile.py`)

### 1.1. Bằng chứng Năng lực (`CandidateEvidence`)
Là đơn vị nguyên tử nhỏ nhất đại diện cho một sự thật về ứng viên:
```python
class CandidateEvidence(BaseModel):
    evidence_id: str          # Mã định danh duy nhất (ví dụ: "ev_exp_steam_camera")
    status: EvidenceStatus    # candidate_confirmed | document_verified | public_verified
    summary: str              # Tóm tắt sự kiện/kỹ năng
    source: str               # Nguồn tài liệu (ví dụ: "cv.pdf", "github_pr")
    source_quote: str | None  # Trích dẫn nguyên văn từ nguồn (bắt buộc khi may đo CV)
    provenance: str | None    # Phân loại gốc: experience, education, identity...
    uncertainty: Literal["low", "medium", "high", "unknown"]
```

### 1.2. Ràng buộc Sự thật Bắt buộc (`FactRequirement`)
Liên kết một sự thật then chốt với các bằng chứng bảo chứng:
```python
class FactRequirement(BaseModel):
    fact_id: str              # Mã sự thật (ví dụ: "fact_cs_student")
    label: str                # Nội dung (ví dụ: "Sinh viên ngành KHMT")
    evidence_ids: list[str]   # Bắt buộc trích dẫn ít nhất 1 evidence_id tồn tại
```
> **Quy tắc Kiểm tra:** Mô hình `CandidateProfile` tự động kiểm tra chéo (`model_validator`). Nếu bất kỳ `fact` nào tham chiếu đến một `evidence_id` không có trong danh sách `evidence`, hệ thống sẽ từ chối lưu và báo lỗi `missing evidence ids`.

---

## 2. Chu kỳ Sống của Hồ sơ (Profile Lifecycle)

```
        [ Bản nháp Onboarding ] (profile_drafts)
                     |
                     |  - OnboardingSession.answer()
                     |  - OnboardingSession.correct()
                     v
        [ Xác thực Cấu trúc ] (profile validation)
                     |
                     |  - Đảm bảo đủ các trường bắt buộc
                     |  - Kiểm tra tính hợp lệ của SHA-256
                     v
        [ Xác nhận Chính thức ] (mocnghe profile confirm / confirm-file)
                     |
                     |  - Ghi nhận thời điểm confirmed_at (UTC)
                     |  - Tính profile_content_hash = SHA-256(payload)
                     v
        [ Hồ sơ Bất biến (Immutable) ] (bảng profiles trong SQLite)
```

### Tính Bất biến (Immutability)
Khi một hồ sơ được xác nhận với phiên bản cụ thể (ví dụ: `version: "1.0"`):
- Toàn bộ nội dung JSON được lưu vào bảng `profiles`.
- Không thể ghi đè (overwrite) một phiên bản đã xác nhận. Bất kỳ thay đổi nào về sau bắt buộc phải nâng phiên bản mới (ví dụ: `"1.1"` hoặc `"2.0"`).
- Điều này đảm bảo rằng các đơn ứng tuyển và bản CV đã nộp trong quá khứ luôn có thể truy vết lại đúng nguyên bản hồ sơ tại thời điểm đó.
