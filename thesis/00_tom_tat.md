# TÓM TẮT KHÓA LUẬN

Trong bối cảnh chuyển đổi số giáo dục, sinh viên đại học cần tra cứu quy chế, học vụ và liên hệ phòng ban một cách nhanh chóng, trong khi các đơn vị hành chính cần kênh quản lý tập trung thông báo, đơn từ và phản hồi. Khóa luận trình bày quá trình nghiên cứu, phân tích, thiết kế và xây dựng **TLU AI Assistant** — hệ thống trợ lý thông minh tích hợp cho sinh viên Trường Đại học Thăng Long, kèm bảng điều khiển web cho cán bộ.

Hệ thống gồm ứng dụng di động đa nền tảng (Flutter), cổng cán bộ (React, Vite), lớp trung gian API (Express), dịch vụ hỏi đáp tri thức (FastAPI, ChromaDB, Google Gemini) và hạ tầng dữ liệu thời gian thực (Firebase Firestore, Storage, Cloud Messaging). Trọng tâm kỹ thuật là mô hình **Retrieval-Augmented Generation (RAG)** với hai chế độ: xử lý tài liệu PDF trên thiết bị (SQLite vector store) và hỏi đáp qua máy chủ (vector Chroma, streaming SSE). Bên cạnh đó, hệ thống hỗ trợ chat theo phòng ban, thông báo toàn trường, nộp đơn hành chính, góp ý và mở cổng web học vụ trong ứng dụng.

Phương pháp tiếp cận kết hợp khảo sát nhu cầu, phân tích hướng đối tượng (use case, sequence diagram), thiết kế kiến trúc phân tầng và triển khai theo Docker Compose. Kết quả đạt được là prototype hoạt động end-to-end: sinh viên hỏi đáp tài liệu quy chế, trao đổi với năm phòng ban, nhận push thông báo; cán bộ quản lý hồ sơ, trả lời chat, phát hành thông báo, quản lý vector tài liệu RAG và ghi nhật ký kiểm toán.

Khóa luận kết luận hệ thống đáp ứng mục tiêu tích hợp AI và tương tác hành chính số; đồng thời chỉ ra hạn chế (xác thực demo, job ingest in-memory) và hướng phát triển (bật đăng nhập email trường, mở rộng quy mô vector DB, kiểm thử tải).

**Từ khóa:** Trợ lý AI; RAG; Flutter; Firestore; hệ thống thông tin giáo dục; Đại học Thăng Long.
