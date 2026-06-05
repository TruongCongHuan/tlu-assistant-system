# CHƯƠNG 1. GIỚI THIỆU

## 1.1. Sự cần thiết của bài toán

Sinh viên đại học trong giai đoạn học tập thường xuyên cần tra cứu thông tin về quy chế đào tạo, điều kiện xét tốt nghiệp, học bổng, quy trình chuyển ngành, bảo lưu, nộp đơn xin phép và các thủ tục hành chính khác. Tại Trường Đại học Thăng Long, các thông tin này được công bố qua website, văn bản PDF và qua từng phòng ban. Khi sinh viên không tìm thấy câu trả lời ngay, họ phải liên hệ trực tiếp qua email, điện thoại hoặc đến trực tiếp — gây tốn thời gian cho cả sinh viên và cán bộ, đặc biệt vào các đợt cao điểm (đăng ký học phần, xét học bổng, cuối kỳ).

Song song đó, nhu cầu **hỏi đáp tự động** dựa trên tài liệu chính thống ngày càng rõ rệt. Các mô hình ngôn ngữ lớn (LLM) có khả năng diễn đạt tự nhiên nhưng dễ “ảo giác” (hallucination) khi không được neo vào nguồn tri thức cụ thể. Kỹ thuật **Retrieval-Augmented Generation (RAG)** khắc phục hạn chế này bằng cách truy vấn các đoạn văn bản liên quan từ kho tài liệu trước khi sinh câu trả lời [1], [2].

Bên cạnh tra cứu, sinh viên cần **kênh tương tác có cấu trúc** với phòng ban: cố vấn học tập, Phòng Công tác Chính trị Sinh viên, Phòng Đào tạo, Phòng Tài chính – Kế toán, Phòng Tham vấn tâm lý. Mỗi phòng có phạm vi nghiệp vụ khác nhau; nếu không có hệ thống thống nhất, lịch sử trao đổi bị phân tán, khó theo dõi và khó đo lường chất lượng phục vụ.

Từ góc độ quản trị, nhà trường cần:

- Phát hành **thông báo** kịp thời tới sinh viên (push notification).
- Tiếp nhận **đơn từ** có file đính kèm và **góp ý** tập trung.
- Quản lý **tài liệu** phục vụ trợ lý AI (upload, cập nhật, xóa vector).
- **Phân quyền** cán bộ và ghi **nhật ký kiểm toán** các thao tác nhạy cảm.

Khóa luận đề xuất giải pháp **TLU AI Assistant** — hệ thống tích hợp trợ lý AI (RAG, giọng nói) và cổng tương tác sinh viên–phòng ban trên nền tảng di động và web cán bộ, nhằm rút ngắn thời gian tra cứu, chuẩn hóa kênh liên lạc và hỗ trợ chuyển đổi số tại TLU.

## 1.2. Mục tiêu nghiên cứu

### 1.2.1. Mục tiêu tổng quát

Xây dựng và đánh giá prototype hệ thống trợ lý AI tích hợp tương tác sinh viên với phòng ban, đáp ứng các nhu cầu tra cứu tri thức và giao tiếp hành chính số tại Trường Đại học Thăng Long.

### 1.2.2. Mục tiêu cụ thể

1. Xác định yêu cầu chức năng và phi chức năng của hệ thống đối với sinh viên và cán bộ.
2. Thiết kế kiến trúc phân tầng: client Flutter, Staff Console (React), BFF (Express), RAG API (FastAPI), Firebase (Firestore, Storage, FCM).
3. Hiện thực pipeline RAG hai chế độ: **on-device** (SQLite + Gemini) và **server** (Chroma + Gemini, SSE).
4. Hiện thực chat phòng ban realtime trên Firestore, thông báo push, nộp đơn và góp ý.
5. Triển khai môi trường Docker Compose, kiểm thử luồng end-to-end và đánh giá kết quả.

## 1.3. Phạm vi nghiên cứu

### 1.3.1. Phạm vi chức năng

| Nhóm | Sinh viên (Flutter) | Cán bộ (Staff Console) |
|------|---------------------|-------------------------|
| Trợ lý AI | Hỏi đáp PDF (local/server), STT, TTS, streaming | Quản lý tài liệu vector RAG |
| Tương tác | Chat 5 phòng ban, thông báo, đơn, góp ý | Trả lời chat, xem đơn/góp ý, phát thông báo |
| Tiện ích | WebView E-Learning, ĐKHP, học phí | Quản lý hồ sơ SV, audit, RBAC |

### 1.3.2. Phạm vi kỹ thuật

- Nền tảng di động: Android và iOS (một codebase Flutter).
- Web cán bộ: React 18, TypeScript, Vite, Tailwind CSS.
- Backend: Express (BFF), FastAPI (RAG), Docker Compose.
- Dữ liệu: Firestore (nghiệp vụ), Chroma (vector server), SQLite (vector local), Firebase Storage (file đơn).

### 1.3.3. Giới hạn

- Chưa triển khai production đầy đủ với xác thực Google `@thanglong.edu.vn` bắt buộc (hỗ trợ anonymous/demo phục vụ báo cáo).
- Không thay thế hệ thống quản lý sinh viên (SIS) lõi của trường.
- Job ingest RAG trên server lưu trạng thái in-memory — mất khi restart container.

## 1.4. Phương pháp tiếp cận

Khóa luận áp dụng quy trình phát triển phần mềm kết hợp **phân tích hướng đối tượng** và **phát triển lặp**:

1. **Khảo sát yêu cầu** từ nghiệp vụ TLU và tài liệu quy chế mẫu.
2. **Thiết kế** use case, sequence diagram, mô hình dữ liệu, security rules.
3. **Cài đặt** theo từng layer: RAG → Firebase → chat → staff console.
4. **Kiểm thử tích hợp** theo checklist E2E trong repository dự án.
5. **Đánh giá** theo tiêu chí chức năng và phi chức năng đã đề ra.

## 1.5. Đóng góp của khóa luận

1. **Đóng góp về giải pháp:** Đề xuất kiến trúc tích hợp trợ lý RAG và tương tác phòng ban trên một hệ sinh thái phần mềm thống nhất cho môi trường đại học.
2. **Đóng góp về kỹ thuật:**
   - So sánh và hiện thực RAG **on-device** (bảo mật/offline một phần) và **server-side** (quản lý tập trung, Chroma).
   - Thiết kế thread chat `{studentUid}_{departmentId}` với Firestore rules theo ownership.
   - Tách auth sinh viên (Firebase) và cán bộ (JWT + bcrypt, không expose `staff_accounts`).
3. **Đóng góp về triển khai:** Bộ Docker Compose, tài liệu deploy Cloud Run, checklist kiểm thử tái lập được.

## 1.6. Cấu trúc khóa luận

Ngoài phần mở đầu, tóm tắt và các mục lục theo quy định nhà trường, nội dung chính gồm bốn chương:

- **Chương 2** trình bày cơ sở lý thuyết về hệ thống thông tin, RAG, kiến trúc phần mềm và khảo sát công nghệ liên quan.
- **Chương 3** trình bày phân tích yêu cầu, thiết kế kiến trúc, mô hình dữ liệu và thiết kế chi tiết các module.
- **Chương 4** trình bày môi trường phát triển, cài đặt, kiểm thử và đánh giá hệ thống.
- **Chương 5** tổng kết kết quả, phân tích hạn chế và đề xuất hướng phát triển.

Khóa luận kết thúc bằng tài liệu tham khảo (chuẩn IEEE) và phụ lục (cấu hình, API, mã nguồn tiêu biểu).
