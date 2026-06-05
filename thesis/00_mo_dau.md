# MỞ ĐẦU

## Bối cảnh nghiên cứu

Giáo dục đại học Việt Nam đang đẩy mạnh chuyển đổi số: đăng ký học phần trực tuyến, E-Learning, thông báo điện tử và quản lý hồ sơ sinh viên trên các hệ thống rời rạc. Sinh viên thường phải tra cứu quy chế, quy trình nộp đơn và liên hệ từng phòng ban (cố vấn học tập, công tác sinh viên, đào tạo, tài chính, tâm lý) qua nhiều kênh — email, điện thoại, fanpage — dẫn đến chậm trễ và thiếu nhất quán thông tin. Song song đó, các mô hình ngôn ngữ lớn (LLM) và kỹ thuật **Retrieval-Augmented Generation (RAG)** cho phép hệ thống trả lời câu hỏi dựa trên tài liệu nội bộ của trường thay vì “bịa” nội dung, phù hợp với bài toán hỏi đáp quy chế và hướng dẫn học vụ [1], [2].

Trường Đại học Thăng Long (TLU) là môi trường triển khai thực nghiệm điển hình: sinh viên cần một điểm chạm thống nhất trên điện thoại; các phòng ban cần dashboard quản lý chat, thông báo, đơn từ và nguồn tri thức phục vụ trợ lý AI. Xuất phát từ yêu cầu đó, khóa luận hướng tới xây dựng **TLU AI Assistant** — sản phẩm phần mềm tích hợp trợ lý AI và kênh tương tác sinh viên–cán bộ.

## Lý do chọn đề tài

- **Tính thời sự:** Ứng dụng AI generative và RAG trong giáo dục là xu hướng được quan tâm trong ngành CNTT và hệ thống thông tin [3].
- **Tính thực tiễn:** Đề tài bám sát nghiệp vụ thật tại TLU (năm phòng ban, thông báo, đơn từ, tài liệu quy chế).
- **Tính kỹ thuật:** Monorepo kết hợp mobile, web, BFF, microservice RAG và Firebase — phù hợp đánh giá năng lực tốt nghiệp ngành CNTT.
- **Khả năng triển khai:** Mã nguồn đã được hiện thực, có Docker Compose và checklist E2E, thuận lợi cho chương thực nghiệm.

## Mục tiêu nghiên cứu

1. Khảo sát và làm rõ yêu cầu chức năng, phi chức năng của hệ thống trợ lý AI và tương tác phòng ban đối với sinh viên TLU.
2. Thiết kế kiến trúc tổng thể, mô hình dữ liệu và các luồng nghiệp vụ chính (RAG, chat, thông báo, đơn từ).
3. Xây dựng prototype: ứng dụng Flutter, Staff Console, BFF Express, RAG API FastAPI, tích hợp Firestore và triển khai Docker.
4. Kiểm thử, đánh giá mức độ đáp ứng yêu cầu và đề xuất hướng phát triển.

## Đối tượng và phạm vi nghiên cứu

**Đối tượng:** Quy trình tra cứu tri thức học vụ/quy chế bằng AI và quy trình tương tác sinh viên–phòng ban trên nền tảng số.

**Phạm vi:**

- **Chức năng:** RAG (local/server), STT/TTS tiếng Việt, chat năm phòng ban, thông báo FCM, nộp đơn (Storage), góp ý, WebView cổng học vụ; phía cán bộ: quản lý SV, chat, thông báo, đơn, góp ý, tài liệu vector, audit, RBAC.
- **Kỹ thuật:** Android/iOS qua Flutter; web cán bộ; không triển khai production quy mô lớn trên cloud trong phạm vi khóa luận (có tài liệu tham khảo Cloud Run).
- **Ngoài phạm vi:** Thay thế hoàn toàn các hệ thống học vụ lõi (SIS, LMS); xử lý thanh toán học phí; nghiên cứu huấn luyện LLM từ đầu.

## Phương pháp nghiên cứu

- **Khảo sát, phân tích:** Tổng hợp yêu cầu từ quy trình thực tế và tài liệu trường.
- **Phân tích – thiết kế hướng đối tượng:** Use case, sequence diagram, mô hình dữ liệu Firestore.
- **Phát triển lặp:** Xây dựng từng module (RAG → Firebase → chat → staff console), kiểm thử tích hợp theo checklist E2E.
- **Thực nghiệm, đánh giá:** Chạy kịch bản demo và đối chiếu tiêu chí chấp nhận.

## Ý nghĩa khoa học và thực tiễn

- **Khoa học:** Áp dụng pipeline RAG (chunking, embedding, retrieval, generation) trong miền dữ liệu giáo dục; so sánh triển khai on-device và server-side.
- **Thực tiễn:** Cung cấp giải pháp tham chiếu cho TLU và các trường tương tự khi triển khai trợ lý AI nội bộ kèm kênh hành chính số.

## Cấu trúc khóa luận

- **Chương 1** trình bày sự cần thiết, mục tiêu, phạm vi, phương pháp và đóng góp đề tài.
- **Chương 2** trình bày cơ sở lý thuyết, công nghệ và khảo sát hệ thống tương tự.
- **Chương 3** phân tích yêu cầu và thiết kế hệ thống (kiến trúc, dữ liệu, giao diện).
- **Chương 4** mô tả cài đặt, triển khai và kiểm thử.
- **Chương 5** tổng kết kết quả, hạn chế và hướng phát triển.

Khóa luận kết thúc bằng tài liệu tham khảo (chuẩn IEEE) và phụ lục.
