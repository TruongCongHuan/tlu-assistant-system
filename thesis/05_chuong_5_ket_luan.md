# CHƯƠNG 5. KẾT LUẬN VÀ HƯỚNG PHÁT TRIỂN

## 5.1. Kết luận

Khóa luận đã hoàn thành việc nghiên cứu, phân tích, thiết kế và xây dựng prototype **TLU AI Assistant** — hệ thống trợ lý AI tích hợp tương tác sinh viên với phòng ban tại Trường Đại học Thăng Long. Hệ thống bao gồm ứng dụng di động Flutter cho sinh viên, cổng web Staff Console cho cán bộ, lớp BFF Express, dịch vụ RAG FastAPI với ChromaDB và hạ tầng Firebase (Firestore, Storage, FCM).

**Các kết quả chính đạt được:**

1. **Về phân tích và thiết kế:** Làm rõ quy trình nghiệp vụ tra cứu tri thức, chat phòng ban, thông báo, đơn từ; thiết kế kiến trúc phân tầng, mô hình dữ liệu Firestore, security rules và RBAC cho cán bộ.

2. **Về hiện thực:** Pipeline RAG hoàn chỉnh (chunking, embedding 768 chiều, retrieval top-5, streaming Gemini) trên cả thiết bị (SQLite) và máy chủ (Chroma); chat realtime với thread `{studentUid}_{departmentId}` cho năm phòng ban; triển khai Docker Compose tái lập được môi trường demo.

3. **Về thực nghiệm:** Các kịch bản kiểm thử end-to-end (health, đăng nhập cán bộ, upload vector, hỏi RAG, chat hai chiều, thông báo FCM, nộp đơn) cho thấy hệ thống đáp ứng các yêu cầu chức năng cốt lõi đã đề ra.

4. **Về đóng góp:** Đề xuất mô hình tích hợp LLM/RAG với kênh hành chính số trong một monorepo, tách bạch auth sinh viên và cán bộ, phù hợp làm tài liệu tham chiếu cho triển khai thực tế tại TLU.

Khóa luận khẳng định: việc kết hợp **Retrieval-Augmented Generation** với **giao tiếp realtime và quản trị tập trung** là hướng đi khả thi để nâng cao trải nghiệm sinh viên và giảm tải cho các phòng ban, trong bối cảnh chuyển đổi số giáo dục đại học.

## 5.2. Hạn chế của hệ thống

1. **Xác thực và demo:** Chế độ anonymous auth và `DemoReportConfig` thuận tiện báo cáo nhưng chưa phản ánh đầy đủ chính sách bảo mật production (bắt buộc email `@thanglong.edu.vn`, tắt bypass auth gate).

2. **Độ bền dịch vụ RAG:** Trạng thái job ingest lưu in-memory trên `rag-api` — mất khi restart container; chưa có hàng đợi persistent (Redis, Firestore jobs).

3. **Kiểm thử tự động:** Thiếu bộ test regression tự động cho Flutter, BFF và FastAPI; phụ thuộc checklist thủ công.

4. **Phụ thuộc bên thứ ba:** Gemini API (quota, độ trễ mạng); chất lượng PDF scan ảnh hưởng extract text.

5. **Lịch sử hội thoại AI:** Chỉ lưu in-memory trên app — sinh viên không đồng bộ lịch sử hỏi đáp AI giữa các thiết bị.

6. **Quy mô:** Chưa thử nghiệm tải lớn (hàng nghìn SV đồng thời), chưa tối ưu chi phí embedding hàng loạt.

## 5.3. Hướng phát triển trong tương lai

### 5.3.1. Ngắn hạn

- Bật **Google Sign-In** bắt buộc domain `@thanglong.edu.vn`; tắt anonymous và demo mode trên bản production.
- Lưu **ingest jobs** trên Firestore hoặc Redis; hỗ trợ resume khi restart service.
- Bổ sung **unit/integration test** CI (GitHub Actions) cho BFF và RAG API.
- **Đa ngôn ngữ** (Anh/Việt) cho UI và prompt RAG.

### 5.3.2. Trung hạn

- Triển khai **Google Cloud Run** theo `docs/DEPLOY_CLOUD_RUN.md` — scale RAG và BFF độc lập.
- **Lưu lịch sử chat AI** (có opt-in) trên Firestore hoặc Cloud Storage đã mã hóa.
- **Phân tích sentiment** góp ý; dashboard thống kê SLA phản hồi phòng ban.
- Tích hợp **calendar** (lịch thi, hạn nộp đơn) qua API học vụ nếu trường mở.

### 5.3.3. Dài hạn

- **Fine-tune** hoặc prompt routing theo từng loại tài liệu (quy chế, học phí, tâm lý).
- **On-device model nhỏ** (Gemma, Phi) giảm phụ thuộc cloud cho câu hỏi đơn giản.
- Mở rộng sang **cổng phụ huynh** hoặc **giảng viên** với RBAC riêng.
- Chứng nhận **bảo mật dữ liệu cá nhân** theo quy định pháp luật Việt Nam về bảo vệ dữ liệu cá nhân.

---

TLU AI Assistant là bước khởi đầu cho nền tảng hỗ trợ sinh viên thông minh tại Trường Đại học Thăng Long. Với các hướng phát triển trên, hệ thống có thể tiến tới triển khai chính thức, phục vụ cộng đồng sinh viên bền vững và mở rộng phạm vi tích hợp với hệ sinh thái học vụ số của nhà trường.
