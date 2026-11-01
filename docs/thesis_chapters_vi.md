# Báo Cáo Kỹ Thuật Hệ Thống Mốc Nghề (mocnghe)

Tài liệu này trình bày toàn bộ cơ sở lý thuyết, phân tích thiết kế hệ thống và hiện thực mã nguồn của Mốc Nghề (`mocnghe`), được đối chiếu trực tiếp từ cấu trúc mã nguồn thực tế tại kho lưu trữ.

---

# 2 Cơ sở lý thuyết

## 2.1 Tổng quan về Trí tuệ nhân tạo & AI Agent trong Quản lý Nghề nghiệp
Trí tuệ nhân tạo (Artificial Intelligence - AI) là lĩnh vực nghiên cứu các hệ thống tính toán có khả năng thực hiện các tác vụ nhận thức, giải quyết vấn đề và hỗ trợ ra quyết định. Trong hệ thống Mốc Nghề, AI được định hình dưới mô hình tác tử hỗ trợ (AI Agent):
- Agent hoạt động như một bộ xử lý thứ cấp (coprocessor) hỗ trợ tự động hóa các thao tác chuẩn bị hồ sơ ứng tuyển, bóc tách thông tin và đề xuất biên soạn câu chữ.
- Mọi tương tác của Agent đều bị ràng buộc bởi các chốt kiểm định tất định (deterministic validation gates).
- Người dùng luôn giữ quyền kiểm soát tối thượng trong mọi quyết định phê duyệt và nộp đơn (human-in-the-loop).

## 2.2 Xử lý ngôn ngữ tự nhiên Tất định (Deterministic Natural Language Processing)
Mốc Nghề không sử dụng mô hình học máy xác suất phức tạp cho các tác vụ phân tích cơ sở, mà triển khai các kỹ thuật NLP tất định (rule-based NLP) hoạt động ngoại tuyến và tức thì:
- **Chuẩn hóa chuỗi văn bản (Text Normalization):** Khử khoảng trắng thừa, chuẩn hóa Unicode UTF-8 cho văn bản tiếng Việt có dấu.
- **Phân đoạn ngữ cảnh theo từ khóa (Contextual Section Splitting):** Nhận diện các khối văn bản của tin tuyển dụng dựa trên từ khóa ranh giới: vùng bắt buộc (`must have`, `yêu cầu`), vùng ưu tiên (`nice to have`, `ưu tiên`) và vùng dừng (`benefits`, `quyền lợi`).
- **Bóc tách cú pháp danh sách (Bullet-point Parsing):** Quét từng dòng văn bản, tự động phát hiện các ký tự đầu mục (`-`, `•`, `*`, `·`, `▪`, `▸`) để phân rã các yêu cầu công việc thành từng phần tử độc lập có mã định danh tuần tự (`req_001`, `req_002`, ...).
- **Kiểm định giao thoa từ vựng bảo thủ (Conservative Word Overlap):** Đối soát chéo giữa yêu cầu của nhà tuyển dụng và đoạn trích dẫn của ứng viên bằng cách kiểm tra sự xuất hiện thực chất của các từ khóa kỹ thuật cốt lõi (`_has_conservative_overlap`), loại trừ các từ dừng (stop words).

## 2.3 Mô hình Ngôn ngữ Lớn (LLMs) & Hàng Rào Phòng Thủ (Safety Guardrails)
Mô hình ngôn ngữ lớn (LLMs) được ứng dụng ở khâu đề xuất biên soạn câu chữ cho CV và thư ứng tuyển (Cover Letter). Hệ thống thiết lập các nguyên tắc phòng thủ nghiêm ngặt:
- **Chống bịa đặt và phóng đại (Anti-Hallucination via Grounding):** LLM không được phép tự thêm thắt kỹ năng, thành tích hay số liệu đo lường ảo. Mọi câu khẳng định (Claim) do mô hình đề xuất đều phải gắn chặt với một bằng chứng thực tế đã được ứng viên xác nhận từ trước.
- **Cách ly dữ liệu không tin cậy (Untrusted Input Isolation):** Mọi văn bản trích xuất từ tin tuyển dụng (JD) hoặc website bên ngoài đều bị coi là dữ liệu thô (untrusted data). Hệ thống loại bỏ nguy cơ tấn công chiếm quyền điều khiển gián tiếp (Indirect Prompt Injection) bằng cách không bao giờ thực thi văn bản này như lệnh hệ thống.
- **Tẩy bỏ thông tin định danh cá nhân (PII Stripping):** Trước khi gửi dữ liệu sang nhà cung cấp mô hình, toàn bộ trường thông tin danh tính (họ tên, email, số điện thoại, địa chỉ) đều bị gỡ bỏ để bảo vệ quyền riêng tư người dùng.

## 2.4 Mô hình Dữ liệu Bằng chứng Nguyên tử (Atomic Evidence Model)
Triết lý cốt lõi của Mốc Nghề là **Evidence-Grounded**:
- **Bằng chứng năng lực nguyên tử (`CandidateEvidence`):** Là đơn vị dữ liệu nhỏ nhất đại diện cho một sự thật đã được chứng thực về ứng viên. Mỗi bằng chứng chứa: mã định danh duy nhất (`evidence_id`), trích dẫn nguyên văn từ tài liệu gốc (`source_quote`), nguồn gốc tài liệu (`source`), phân loại xuất xứ (`provenance`) và mức độ tin cậy (`uncertainty`).
- **Ràng buộc sự thật bắt buộc (`FactRequirement`):** Một nhận định tổng quát về ứng viên chỉ được hệ thống chấp nhận nếu liên kết với ít nhất một bằng chứng hợp lệ. Mô hình dữ liệu tự động kiểm tra chéo, từ chối lưu trữ nếu xuất hiện sự thật mồ côi (không có bằng chứng chứng minh).

## 2.5 Kiểm Tra Toàn Vẹn & Chống Giả Mạo Bằng Mã Băm SHA-256 (Tamper-Evident Hashing)
Hệ thống áp dụng các hàm băm mật mã học SHA-256 để kiểm soát tính toàn vẹn của mọi thực thể:
- **Băm danh tính tin tuyển dụng (`hash_job_identity`):** Chuẩn hóa khoảng trắng toàn văn nội dung JD để sinh mã định danh duy nhất, ngăn ngừa trùng lặp dữ liệu.
- **Băm nội dung hồ sơ và bản thảo (`content_hash`):** Mỗi phiên bản hồ sơ ứng viên và bản thảo CV đều có một mã băm SHA-256 đại diện cho trạng thái nội dung tại thời điểm đó.
- **Cơ chế phát hiện can thiệp (Tamper Detection):** Khi hệ thống đọc dữ liệu từ tệp lưu trữ, mã băm sẽ được tính toán lại độc lập. Nếu phát hiện sai lệch so với mã băm lưu trữ, hệ thống lập tức ném lỗi và từ chối xử lý, ngăn chặn hoàn toàn việc sửa đổi dữ liệu trái phép.

## 2.6 Kiến trúc Local-First & Lưu Trữ Dựa Trên Tệp (File-Based Storage)
Mốc Nghề tuân thủ nguyên tắc Local-First thông qua hệ thống tệp tin minh bạch, dễ dàng quản lý phiên bản bằng Git:
- **Chủ quyền dữ liệu (Data Sovereignty):** Toàn bộ dữ liệu hồ sơ cá nhân, lịch sử ứng tuyển, tin tuyển dụng và các bản ghi kiểm toán được lưu trữ cục bộ trên máy trạm của người dùng dưới dạng các tệp văn bản có cấu trúc:
  - **Markdown kèm Frontmatter YAML:** Lưu trữ tin tuyển dụng (`jobs/*.md`), hồ sơ ứng viên (`profiles/*.md`), bản thảo CV (`cvs/*.md`) và báo cáo đánh giá (`reports/*.md`).
  - **YAML & JSON:** Lưu trữ dữ liệu cấu trúc máy đọc cho việc nạp và xử lý tự động (`*.yaml`, `profile.json`).
  - **Bảng tổng hợp tiến trình (`pipeline.md`):** Tự động cập nhật trực quan toàn bộ phễu nộp đơn theo từng trạng thái.
- **Hoạt động độc lập ngoại tuyến (Offline Availability):** Toàn bộ quy trình từ quản lý hồ sơ, bóc tách JD, đánh giá độ phù hợp (triage), kiểm tra mã băm cho đến kết xuất PDF đều vận hành bình thường mà không cần kết nối mạng Internet.

## 2.7 Hợp Đồng Dữ Liệu Tĩnh & Chỉ Dẫn Nghiêm Ngặt (Structured Contracts & Prompt Directives)
Giao tiếp giữa hệ thống Mốc Nghề và các mô hình ngôn ngữ lớn được chuẩn hóa thành các hợp đồng dữ liệu có cấu trúc:
- **Gói may đo tĩnh (`TailoringPacket`):** Đóng gói ngữ cảnh công việc mục tiêu, các bằng chứng đã chọn lọc và bản chỉ dẫn hệ thống bất biến. Gói dữ liệu được ký số bằng mã băm `packet_hash`.
- **Ràng buộc phản hồi khắt khe (`TailoringResponse`):** Mô hình trả về kết quả tuân thủ nghiêm ngặt schema Pydantic, bảo toàn tuyệt đối danh sách và thứ tự các mã `evidence_id`, cấm các thuộc tính dư thừa (`extra="forbid"`).

---

# 3 Phân tích và thiết kế hệ thống

## 3.1 Phân tích yêu cầu hệ thống

### 3.1.1 Yêu cầu chức năng
1. **Thu thập tin tuyển dụng (Job Ingestion):**
   - Hỗ trợ nạp dữ liệu từ đường dẫn web (URL), tệp văn bản thô, hoặc luồng nhập chuẩn `stdin`.
   - Cung cấp các adapter bóc tách chuyên biệt cho các cổng tuyển dụng (Greenhouse, ITviec, Indeed, VietnamWorks) và cơ chế thích ứng chung (Generic Fallback) cho các website bất kỳ.
   - Hỗ trợ trình duyệt không đầu (Playwright Headless) cho các trang tải nội dung bằng JavaScript (SPA) hoặc có hàng rào Cloudflare.
   - Tự động khử trùng lặp dữ liệu tuyển dụng dựa trên mã băm nội dung.
2. **Quản lý Hồ sơ & Bằng chứng Năng lực (Profile Management):**
   - Quản lý kho bằng chứng nguyên tử (`CandidateEvidence`) và các ràng buộc sự thật (`FactRequirement`).
   - Cung cấp quy trình kiểm định cấu trúc và phê duyệt phiên bản hồ sơ bất biến (Immutable Profiles): một phiên bản đã xác nhận không thể bị ghi đè.
3. **Sàng lọc & Đánh giá Độ phù hợp (Triage & Evaluation):**
   - Tự động bóc tách các gạch đầu dòng yêu cầu từ JD thành danh sách mã định danh tuần tự (`req_001`, `req_002`, ...).
   - Thực hiện sàng lọc tức thì ngoại tuyến dựa trên các điều kiện cứng (lương sàn, ngành cấm, địa điểm).
   - Đóng gói dữ liệu đánh giá an toàn (`export-packet`) đã loại bỏ PII để AI Agent phân tích và nhập báo cáo kết quả có kiểm định chéo (`import-report`).
4. **May đo Hồ sơ & Thư ứng tuyển (CV & Cover Letter Tailoring):**
   - Tuyển chọn và sắp xếp các khẳng định năng lực (`Claim`) phù hợp với yêu cầu của JD.
   - Hỗ trợ hai chế độ hiển thị khẳng định: giữ nguyên văn trích dẫn gốc (`mode="extractive"`) hoặc đề xuất biên soạn lại câu chữ/dịch thuật (`mode="proposed"`).
   - Tự động sinh Cover Letter song ngữ dựa trên các bằng chứng đã duyệt.
5. **Cổng Phê duyệt & Kết xuất In ấn (Approval Gate & PDF Rendering):**
   - Cơ chế kiểm soát mã băm: Hệ thống từ chối kết xuất nếu nội dung CV chưa được người dùng phê duyệt tường minh bằng mã băm SHA-256.
   - Kết xuất PDF chuẩn in ấn A4 qua ReportLab Native Engine hoặc Modern HTML Engine; kiểm soát nghiêm ngặt số trang in (`--max-pages`).
6. **Theo dõi Đơn Tuyển dụng Tuyến tính (Application Tracking):**
   - Quản lý máy trạng thái tuyến tính cho tiến trình nộp đơn (`discovered` → `shortlisted` → `drafting` → `ready` → `applied` → `interviewing`...).
   - Lưu trữ ảnh chụp nộp đơn bất biến (`submission_snapshot`) kèm mã băm SHA-256.

### 3.1.2 Yêu cầu phi chức năng
- **Bảo mật và Quyền riêng tư (Local-First):** Toàn bộ dữ liệu hồ sơ cá nhân và lịch sử ứng tuyển lưu trữ cục bộ dưới dạng các tệp văn bản trong workspace. Không gửi thông tin PII lên dịch vụ mạng bên ngoài.
- **Tính toàn vẹn và Chống giả mạo (Audit & Tamper-Evident):** Mọi bản ghi quan trọng đều được bảo chứng bằng mã băm SHA-256. Mọi hành vi sửa đổi dữ liệu ngoài quy trình đều bị phát hiện và ngăn chặn.
- **Tính xác thực (Evidence-Grounded):** Tuyệt đối không sinh dữ liệu ảo hoặc phóng đại thành tích. Mọi khẳng định trên hồ sơ đều có bằng chứng gốc làm căn cứ.
- **Quyền kiểm soát thuộc con người (Human-in-the-Loop):** Hệ thống không tự động nộp đơn. Lệnh xác nhận nộp đơn (`apply`) đòi hỏi hành động tường minh từ người dùng.
- **Hiệu năng cao:** Các tác vụ kiểm tra toàn vẹn, bóc tách cấu trúc, sàng lọc triage và render PDF native thực thi tức thì (dưới 1 giây).

### 3.1.3 Đối tượng sử dụng hệ thống
- **Người tìm việc / Ứng viên (Job Seekers):** Quản lý tập trung kho thành tích cá nhân, may đo CV và thư ứng tuyển chính xác cho từng vị trí, theo dõi tiến độ nộp đơn minh bạch.
- **Tác tử AI Tự hành (Autonomous Coding Agents):** Các agent (Hermes, Cursor, Claude Code) điều khiển hệ thống qua CLI hoặc Slash Commands để hỗ trợ người dùng thực hiện chu trình tìm việc an toàn.

## 3.2 Kiến trúc hệ thống
Hệ thống Mốc Nghề được xây dựng theo kiến trúc phân tầng module hóa hướng dịch vụ cục bộ (Local Modular Architecture):

```
+-------------------------------------------------------------------------------+
|                       Giao diện Người dùng & AI Agent                         |
|      - Typer CLI Engine (Dòng lệnh trực tiếp)                                 |
|      - Slash Commands & Rules (.cursor/rules, .agents/skills, ~/.hermes)      |
+---------------------------------------+---------------------------------------+
                                        |
      +---------------------------------+---------------------------------+
      |                                                                   |
      v                                                                   v
+-------------------------------+                       +-------------------------------+
|     Ingestion Subsystem       |                       | Candidate & Career Subsystem  |
| - Adapter Registry            |                       | - Profile & Evidence Engine   |
|   (Greenhouse, ITviec, Indeed)|                       | - Deterministic Triage Engine |
| - Generic Fallback Adapter    |                       | - CV Tailoring & Claims Engine|
| - Playwright Headless Browser |                       | - Cover Letter Generator      |
| - Deduplication & SHA-256     |                       | - Linear Application Tracker  |
+---------------+---------------+                       +---------------+---------------+
                |                                                       |
                +---------------------------+---------------------------+
                                            |
                                            v
+-------------------------------------------------------------------------------+
|                      Local File-Based Storage Engine                          |
| - Markdown Files with YAML Frontmatter (jobs/, profiles/, cvs/, reports/)     |
| - Structured YAML & JSON Data Files (applications/, profile.yaml/json)        |
| - Visual Application Pipeline Summary (pipeline.md)                           |
| - Content Hash & Tamper Detection (SHA-256)                                   |
+-------------------------------------------------------------------------------+
```

### 3.2.1 Giai đoạn xây dựng cơ sở dữ liệu tri thức
Giai đoạn này tiếp nhận và chuẩn hóa các nguồn dữ liệu nền tảng:
1. **Thiết lập Hồ sơ Năng lực (Profile Onboarding):**
   - Tiếp nhận thông tin hồ sơ ứng viên qua tệp cấu trúc `profile.yaml` / `profile.json` hoặc giao diện dòng lệnh.
   - Chuẩn hóa thành các thực thể `CandidateEvidence` và ràng buộc `FactRequirement`.
   - Xác thực liên kết logic chéo giữa sự thật và bằng chứng.
   - Xác nhận hồ sơ chính thức, tính mã băm `profile_content_hash`, đóng băng phiên bản và lưu thành tệp cấu trúc YAML (`profiles/<version>.yaml`) cùng bản hiển thị Markdown (`profiles/<version>.md`).
2. **Thu thập và Chuẩn hóa Tin tuyển dụng (Job Ingestion):**
   - Đọc dữ liệu từ URL, file hoặc stdin qua Adapter phù hợp.
   - Bóc tách các trường thông tin cấu trúc: chức danh, công ty, địa điểm, mô tả, yêu cầu, quyền lợi.
   - Chuẩn hóa khoảng trắng toàn văn nội dung, tính mã băm `hash_job_identity()`, sinh mã `job_id`.
   - Lưu trữ thành tệp Markdown có cấu trúc Frontmatter YAML (`jobs/<job_id>.md`) và khởi tạo tệp theo dõi đơn (`applications/<job_id>.yaml`).

### 3.2.2 Giai đoạn truy vấn và sinh câu trả lời
Giai đoạn này phối hợp thông tin giữa hồ sơ ứng viên và tin tuyển dụng để tạo ra bộ hồ sơ ứng tuyển hoàn chỉnh:
1. **Sàng lọc & Khớp nối (Triage & Matching):**
   - Phân tích bóc tách các yêu cầu (`req_xxx`) từ tệp JD Markdown.
   - Sàng lọc nhanh các điều kiện cứng và đề xuất các bằng chứng phù hợp từ tệp hồ sơ.
2. **Đóng gói Ngữ cảnh (Tailoring Packet Export):**
   - Trích xuất tập con bằng chứng liên quan.
   - Lược bỏ dữ liệu danh tính cá nhân (PII).
   - Đóng gói cùng bản chỉ dẫn an toàn thành cấu trúc JSON và ký số bằng mã băm SHA-256 (`packet_hash`).
3. **May đo Nội dung (Controlled Generation):**
   - Tác tử AI / LLM đề xuất biên soạn câu chữ cho các khẳng định năng lực (`Claim`), ánh xạ khớp với các yêu cầu của JD.
   - Bắt buộc bảo toàn nguyên vẹn mã định danh bằng chứng và câu trích dẫn gốc.
4. **Kiểm định và Nhập Bản thảo (Response Validation & Draft Import):**
   - Hệ thống kiểm tra tính toàn vẹn của mã băm `packet_hash` và thứ tự danh sách bằng chứng trong phản hồi.
   - Lưu trữ bản thảo CV mới thành tệp cấu trúc YAML (`cvs/<cv_id>.yaml`) và tệp Markdown hiển thị (`cvs/<cv_id>.md`).
5. **Cổng Phê duyệt Người dùng (Human Approval Gate):**
   - Người dùng xem xét nội dung bản thảo và lấy mã băm SHA-256.
   - Người dùng phê duyệt thông qua lệnh `cv approve` kèm mã băm chính xác, hệ thống ghi nhận tệp phê duyệt `cvs/<cv_id>.approval.yaml`.
6. **Kết xuất Thành phẩm (Document Rendering):**
   - Trình render đọc bản CV đã được duyệt từ tệp YAML, biên dịch ra tệp PDF thành phẩm và bản manifest JSON.

## 3.3 Quy trình xử lý dữ liệu

### 3.3.1 Quy trình xây dựng cơ sở dữ liệu tri thức
Quy trình nạp và quản lý tri thức diễn ra qua các bước tuần tự:

```
[ Hồ sơ Ứng viên ] ──> [ Onboarding Parser ] ──> [ Validate Facts/Evidence ] ──> [ Băm SHA-256 ] ──> [ profiles/<ver>.yaml & md ]

[ Nguồn JD Tuyển dụng ] ──> [ Adapter Dispatcher ] ──> [ Bóc tách DOM/JSON-LD ] ──> [ Băm SHA-256 ] ──> [ jobs/<job_id>.md ]
```

1. **Tiếp nhận dữ liệu:** Nạp hồ sơ người dùng hoặc nội dung JD từ nguồn ngoài.
2. **Chuẩn hóa cấu trúc:** Chuyển đổi định dạng văn bản thô về các mô hình dữ liệu Pydantic (`CandidateProfile`, `Job`).
3. **Kiểm tra tính hợp lệ dữ liệu:** Xác thực liên kết giữa facts và evidence_ids; phát hiện lỗi định dạng.
4. **Băm bảo vệ toàn vẹn:** Tính toán giá trị băm SHA-256 cho nội dung đã chuẩn hóa.
5. **Ghi tệp lưu trữ cục bộ:** Lưu trữ vào các thư mục chuyên biệt trong workspace với định dạng Markdown và YAML.

### 3.3.2 Quy trình truy vấn và sinh câu trả lời
Quy trình phối hợp nghiệp vụ giữa các phân hệ:

```
[ jobs/ + profiles/ ] ──> [ Trích xuất Req / Evidence ] ──> [ Tẩy bỏ PII ] ──> [ Đóng gói Packet ]
                                                                                      │
                                                                                      ▼
[ cvs/<id>.yaml & md ] <── [ Kiểm tra Packet Hash ]       <── [ LLM / Agent ] <───────┘
       │
       ▼
[ Review & Hash ]      ──> [ cv approve --hash ]          ──> [ cvs/<id>.approval.yaml ]
                                                                      │
                                                                      ▼
                                                               [ PDF Renderer ] ──> [ cv.pdf + cv.json ]
```

1. **Trích xuất dữ liệu nguồn:** Đọc tin tuyển dụng mục tiêu từ thư mục `jobs/` và hồ sơ ứng viên hợp lệ từ thư mục `profiles/`.
2. **Khử danh tính nhạy cảm:** Gỡ bỏ toàn bộ thông tin PII nhằm bảo vệ quyền riêng tư người dùng.
3. **Đóng gói và băm nội dung:** Tạo gói dữ liệu tĩnh kèm mã băm xác thực `packet_hash`.
4. **Biên soạn có bảo chứng:** AI Agent / LLM thực hiện căn chỉnh văn phong dựa trên bằng chứng được cấp.
5. **Đối soát và nhập dữ liệu:** Xác thực tính toàn vẹn của phản hồi trước khi ghi vào thư mục `cvs/`.
6. **Phê duyệt tường minh:** Người dùng thực hiện phê duyệt bản thảo thông qua mã băm SHA-256, tạo tệp `.approval.yaml`.
7. **Kết xuất tài liệu:** Trình biên dịch tạo tài liệu PDF chuẩn in ấn A4.

## 3.4 Thiết kế Cấu Trúc Lưu Trữ Dựa Trên Tệp (File-Based Storage Design)
Hệ thống sử dụng không gian làm việc (workspace) độc lập với cấu trúc thư mục phân cấp rõ ràng:

```
workspace/
├── profile.yaml / profile.json      # Hồ sơ ứng viên nguồn
├── pipeline.md                      # Bảng tổng hợp trạng thái nộp đơn trực quan
├── jobs/                            # Tin tuyển dụng đã thu thập
│   └── <job_id>.md                  # Markdown kèm Frontmatter YAML lưu cấu trúc JD
├── profiles/                        # Các phiên bản hồ sơ đã xác nhận (bất biến)
│   ├── <version>.yaml               # Cấu trúc dữ liệu Pydantic đầy đủ
│   └── <version>.md                 # Bản hiển thị trực quan cho con người đọc
├── drafts/                          # Bản nháp hồ sơ trong quá trình onboarding
│   └── <draft_id>.yaml              # Payload cấu trúc phiên hỏi đáp
├── cvs/                             # Các phiên bản bản thảo CV và phê duyệt
│   ├── <cv_id>.yaml                 # Dữ liệu cấu trúc danh sách Claims
│   ├── <cv_id>.md                   # Định dạng CV Markdown trực quan
│   └── <cv_id>.approval.yaml        # Bản ghi phê duyệt kèm mã băm SHA-256
├── reports/                         # Báo cáo đánh giá độ phù hợp (Triage/Evaluation)
│   ├── <report_id>.yaml             # Kết quả đánh giá chi tiết theo từng yêu cầu
│   └── <report_id>.md               # Báo cáo tổng hợp khuyến nghị và phát hiện
└── applications/                    # Trạng thái nộp đơn và lịch sử sự kiện
    └── <job_id>.yaml                # Trạng thái hiện tại, CV đính kèm, và nhật ký chuyển trạng thái
```

### Cấu trúc Dữ liệu Chi tiết trong từng Phân hệ Tệp
- **Tin tuyển dụng (`jobs/<job_id>.md`):**
  - Phần Frontmatter YAML lưu trữ: `job_id`, `content_hash`, `title`, `employer`, `location`, `workplace_policy`, `employment_type`, `salary`, `source` (nguồn gốc, URI gốc, thời điểm thu thập), và trạng thái `applied`.
  - Phần thân Markdown chứa toàn văn mô tả công việc, yêu cầu tuyển dụng và quyền lợi dưới dạng trực quan.
- **Phiên bản Hồ sơ Bất biến (`profiles/<version>.yaml`):**
  - Chứa toàn bộ cây dữ liệu: thông tin liên hệ, mục tiêu nghề nghiệp, kinh nghiệm, học vấn, danh sách kỹ năng, ngôn ngữ, cùng toàn bộ danh sách `CandidateEvidence` và `FactRequirement`.
  - Tệp được khóa bất biến theo số hiệu phiên bản; không cho phép ghi đè một phiên bản đã xác nhận.
- **Tiến trình Ứng tuyển (`applications/<job_id>.yaml` & `pipeline.md`):**
  - `applications/<job_id>.yaml`: Lưu giữ trạng thái hiện tại (`state`), phiên bản CV mục tiêu (`cv_version`), mã băm nội dung JD (`jd_content_hash`), thời điểm nộp đơn, cùng mảng danh sách lịch sử chuyển trạng thái `events`.
  - `pipeline.md`: Tự động tái tạo sau mỗi lần chuyển trạng thái, hiển thị phân mục theo các nhóm trạng thái (`Discovered`, `Shortlisted`, `Drafting`, `Ready`, `Applied`, `Interviewing`, `Offer`, `Rejected`, `Withdrawn`, `Archived`) kèm thời điểm cập nhật mới nhất.

---

# 4 Xây dựng hệ thống

## 4.1 Thu thập dữ liệu (Job Ingestion)
Phân hệ `ingestion` được hiện thực hóa tại gói `src/mocnghe/ingestion/`:
- **Kiến trúc Registry & Adapter:**
  Lớp trừu tượng `BaseJobAdapter` định nghĩa giao diện chung (`supports_url`, `parse_job`, `fetch_job`). Lớp `Registry` tự động điều phối URL đầu vào tới adapter tương ứng:
  - `GreenhouseAdapter`: Trích xuất dữ liệu tuyển dụng từ Greenhouse qua selector DOM tiêu chuẩn.
  - `ITviecAdapter`: Bóc tách cấu trúc việc làm ngành IT tại Việt Nam, xử lý phát hiện thử thách bảo vệ bot Cloudflare.
  - `IndeedAdapter`: Ưu tiên bóc tách từ cấu trúc dữ liệu JSON-LD Schema chuẩn (`JobPosting`), kết hợp biến trạng thái `window._initialData` và selector DOM dự phòng.
  - `VietnamWorksAdapter`: Bóc tách dữ liệu việc làm từ nền tảng VietnamWorks.
  - `GenericAdapter`: Cơ chế dự phòng thông minh cho mọi website lạ, khai thác OpenGraph metadata và các thẻ ngữ nghĩa HTML (`<main>`, `<article>`).
- **Phương thức Tải Dữ liệu:**
  - Sử dụng thư viện `httpx` với cấu hình User-Agent hiện đại và timeout bảo vệ cho các trang web tĩnh.
  - Tích hợp trình duyệt tự động `Playwright` Headless Chromium cho các Single Page Applications (SPA) đòi hỏi thực thi JavaScript để hiển thị nội dung.
- **Khử trùng lặp và Chuẩn hóa:**
  Hàm `hash_job_identity()` chuẩn hóa khoảng trắng trong toàn văn nội dung, tính mã SHA-256 và sinh mã `job_<16 hex>`. Nếu nguồn tin đã tồn tại, hệ thống cập nhật nội dung thay vì tạo bản ghi rác.

## 4.2 Tiền xử lý dữ liệu (Data Preprocessing)
Khâu tiền xử lý dữ liệu chuẩn bị các khối thông tin đạt chuẩn trước khi phân tích hoặc lưu trữ:
1. **Làm sạch và Escape Nội dung:** Chuẩn hóa mã hóa UTF-8 cho tiếng Việt có dấu, và escape các ký tự đặc biệt XML/HTML qua `xml.sax.saxutils.escape` để ngăn chặn lỗi biên dịch tài liệu PDF.
2. **Bóc tách Yêu cầu Tuyển dụng Tự động (`evaluation_runtime.py`):**
   - Quét văn bản theo từng dòng, nhận diện vùng tiêu đề qua từ khóa ngữ cảnh: bắt buộc (`required qualifications`, `must have`, `yêu cầu`), ưu tiên (`nice to have`, `ưu tiên`) và vùng dừng (`benefits`, `quyền lợi`).
   - Tách các gạch đầu dòng dựa trên ký tự phân tách (`-`, `•`, `*`, `·`, `▪`, `▸`), gán nhãn trạng thái và định danh tuần tự (`req_001`, `req_002`, ...).
3. **Chuẩn hóa Bằng chứng Hồ sơ (`profile.py`):**
   - Chuẩn hóa các bằng chứng năng lực thành `CandidateEvidence`, gán mức độ bất định (`uncertainty`).
   - Kiểm tra liên kết toàn vẹn của `FactRequirement` qua validator tự động của Pydantic, đảm bảo không có khẳng định sự thật nào bị mồ côi bằng chứng.

## 4.3 Quản Lý Khẳng Định Năng Lực & May Đo Hồ Sơ (Claims & Tailoring Engine)
Phân hệ `cv` và `cv_render` quản lý việc tuyển chọn bằng chứng và tinh chỉnh văn phong phù hợp với từng JD cụ thể:
- **Mô hình Khẳng định Năng lực (`Claim` trong `cv.py`):**
  Một bản CV trong Mốc Nghề là một danh sách các khẳng định có cấu trúc:
  - `evidence_id`: Trỏ trực tiếp về mã bằng chứng đã xác nhận.
  - `source_quote`: Câu trích dẫn gốc trong bằng chứng chứng thực.
  - `text`: Câu hiển thị trên bản CV xuất xưởng.
  - `mode`: Chế độ hiển thị (`extractive` nếu giữ nguyên văn trích dẫn gốc; `proposed` nếu được viết lại văn phong hoặc dịch ngữ).
- **Chuẩn hóa Phân mục Tự động:**
  Hệ thống sử dụng `@field_validator` để tự động chuẩn hóa các phân mục thông dụng sang enum chuẩn: `summary` và `projects` chuyển thành `other`; `certifications` chuyển thành `credentials`.

## 4.4 Lưu Trữ Bền Vững Dựa Trên Tệp & Kiểm Tra Băm Toàn Vẹn (File Storage & Hash Auditing)
Phân hệ lưu trữ được hiện thực hóa qua lớp `CareerRepository` (`src/mocnghe/storage/repository.py`):
- **Xác thực Mã băm khi Đọc (`digest` check):**
  Khi truy vấn một bản thảo CV từ thư mục `cvs/`, hệ thống đọc tệp YAML và tính toán lại mã băm nội dung. Nếu mã băm không khớp với giá trị ghi nhận trong tệp hoặc bản phê duyệt, hệ thống lập tức ném ngoại lệ vi phạm tính toàn vẹn.
- **Quản lý Bản thảo Đơn Ứng tuyển (`application_drafts.py`):**
  Lưu trữ câu trả lời cho các câu hỏi tuyển dụng dạng biểu mẫu, liên kết với mã băm phê duyệt trong các tệp YAML tương ứng.
- **Cơ chế Tự Chẩn Đoán (`mocnghe doctor`):**
  Tự động kiểm tra tính sẵn sàng của các thư mục lưu trữ (`jobs/`, `profiles/`, `reports/`, `drafts/`, `applications/`), thống kê số lượng bản ghi thực tế và báo cáo trạng thái hệ thống.

## 4.5 Phân Hệ Đánh Giá & Sàng Lọc Sơ Bộ (Triage & Evaluation Engine)
Được hiện thực hóa tại `src/mocnghe/triage.py` và `src/mocnghe/evaluation_runtime.py`:
- **Đánh giá Sơ bộ Tức thì (Deterministic Triage):**
  Hàm `triage_job(profile, job)` đối chiếu hồ sơ ứng viên và tin tuyển dụng hoàn toàn ngoại tuyến:
  - Kiểm tra tiêu chí cứng (Hard Constraints): mức lương sàn, ngành nghề cấm, chứng chỉ bắt buộc.
  - Kiểm tra vùng chưa rõ (Unknowns): hình thức làm việc, địa điểm chưa rõ ràng.
  - Trả về kết luận rõ ràng: `practical_fit` (đủ điều kiện), `evaluate_with_unknowns` (cần làm rõ thêm), hoặc `not_fit` (vi phạm điều kiện cứng).
- **Kiểm định Gói Đánh giá AI Agent:**
  Khi nhận báo cáo đánh giá JSON từ AI Agent (`import-report`), hệ thống kiểm định:
  - Bắt buộc đánh giá đúng thứ tự toàn bộ các mã yêu cầu `req_xxx`.
  - Bắt buộc trích dẫn nguyên văn `source_quote` có sẵn trong gói.
  - Thực hiện kiểm tra giao thoa từ vựng thực chất (`_has_conservative_overlap`) giữa câu trích dẫn và nội dung yêu cầu tuyển dụng.
  - Ghi nhận báo cáo kết quả đồng thời ra hai định dạng: `reports/<report_id>.yaml` (cho máy đọc) và `reports/<report_id>.md` (cho con người xem).

## 4.6 Tích Hợp Mô Hình Ngôn Ngữ Lớn An Toàn (Secure LLM Runtime)
Phân hệ tích hợp LLM được thực thi tại `src/mocnghe/cv_runtime.py`:
- **Đóng gói Hợp đồng Dữ liệu (Tailoring Packet Contract):**
  - Hàm `create_packet()` đóng gói dữ liệu công việc và danh sách các Claims theo schema chuẩn `m4.tailoring.v1`.
  - Toàn bộ gói dữ liệu được băm SHA-256 thành `packet_hash`.
  - Chỉ dẫn hệ thống bất biến (`INSTRUCTIONS`) nghiêm cấm LLM tự sinh thành tích hoặc thực thi chỉ dẫn nhúng trong JD.
- **Điều phối Giao tiếp Mạng An toàn (`_request_with_deadline`):**
  - Thực thi kết nối bất đồng bộ qua `httpx.AsyncClient` với cơ chế kiểm soát thời gian chết tuyệt đối (`asyncio.timeout`).
  - Giới hạn kích thước gói phản hồi tối đa (`max_response_bytes`), ngăn ngừa hiện tượng tràn bộ nhớ.
- **Xác thực Đầu ra Ngược (Canonical Response Validation):**
  - Hàm `import_response()` kiểm định dữ liệu trả về từ LLM thông qua Pydantic model `TailoringResponse`.
  - Bắt buộc `packet_hash` trong phản hồi phải khớp chính xác với gói ban đầu.
  - Bắt buộc danh sách `evidence_id` trong các claims trả về phải bảo toàn tuyệt đối số lượng và thứ tự gốc.
  - Ghi nhận xuất xứ nguồn gốc phiên bản (`provenance=f"direct:{config.model}"`).

## 4.7 Giao Diện Người Dùng, Tác Tử AI & Bộ Kết Xuất PDF
Mốc Nghề triển khai giao diện theo triết lý **Giao diện Kép Đối xứng (Dual-Interface Parity)**:
1. **Giao diện Dòng lệnh Hiện đại (Typer CLI Engine - `cli.py`):**
   - Cung cấp cây lệnh phân cấp trực quan:
     - `mocnghe jobs`: Thu thập, tìm kiếm và hiển thị tin tuyển dụng.
     - `mocnghe profile`: Quản lý, kiểm định và xác nhận hồ sơ cá nhân.
     - `mocnghe evaluate`: Sàng lọc triage và xuất/nhập gói đánh giá.
     - `mocnghe cv`: Vòng đời tạo lập, chỉnh sửa, phê duyệt và xuất bản CV.
     - `mocnghe draft`: Quản lý bản thảo đơn xin việc và Cover Letter.
     - `mocnghe track` & `apply`: Quản lý tiến trình nộp đơn với máy trạng thái tuyến tính.
2. **Giao diện Tác tử AI (AI Agent & Hermes Skills Layer):**
   - Tích hợp sâu vào các môi trường tác tử thông minh (Hermes Agent, Cursor, Claude Code) qua các tệp quy tắc chuẩn:
     - `.cursor/rules/mocnghe.md`: Chỉ dẫn ngữ cảnh tự động cho Cursor IDE.
     - `.agents/skills/mocnghe/SKILL.md`: Chuẩn kỹ năng cho Autonomous AI Agents.
     - Hermes Skill (`~/.hermes/skills/productivity/mocnghe/`): Hỗ trợ tương tác hội thoại tự nhiên thông qua các Slash Commands (`/crawl`, `/onboard`, `/triage`, `/tailor`, `/track`, `/apply`).
   - Cổng phê duyệt bắt buộc: Agent chỉ có thể đề xuất chỉnh sửa, không thể tự ý phê duyệt nếu không có mã băm SHA-256 từ con người, và không thể tự ý gửi đơn nộp.
3. **Bộ Kết xuất Hồ sơ Đa Engine (PDF Rendering Engines):**
   - **ReportLab Native Engine (`cv_render.py`):** Engine độc lập bằng Python, tối ưu tốc độ kết xuất, hỗ trợ đầy đủ phông chữ tiếng Việt có dấu, kiểm soát nghiêm ngặt ngân sách số trang in (`--max-pages`).
   - **Modern HTML Engine (`cv_modern_render.py`):** Kết xuất giao diện hiện đại bằng HTML/CSS và Playwright, hiển thị trực quan các dải màu và thẻ kỹ năng.
