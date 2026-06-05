# CHƯƠNG 2. CƠ SỞ LÝ THUYẾT VÀ CÔNG NGHỆ LIÊN QUAN

## 2.1. Tổng quan lý thuyết hệ thống thông tin trong giáo dục

### 2.1.1. Khái niệm hệ thống thông tin

Hệ thống thông tin (Information System — IS) là tập hợp có tổ chức gồm con người, quy trình, dữ liệu và công nghệ nhằm thu thập, xử lý, lưu trữ và phân phối thông tin phục vụ ra quyết định và vận hành tổ chức [4]. Trong môi trường đại học, IS hỗ trợ quản lý đào tạo, tuyển sinh, tài chính sinh viên và giao tiếp với sinh viên.

### 2.1.2. Vai trò của IS trong tổ chức giáo dục

IS giáo dục giúp:

- **Chuẩn hóa quy trình** (đăng ký học phần, xét điểm, cấp bằng).
- **Tăng tính minh bạch** thông qua công bố quy chế và thông báo điện tử.
- **Giảm chi phí giao dịch** khi chuyển tương tác sang kênh số.
- **Hỗ trợ ra quyết định** dựa trên dữ liệu tổng hợp (báo cáo, thống kê).

Đề tài bổ sung lớp **tương tác thông minh** (AI) và **realtime** (Firestore) trên nền IS hiện có của trường, thay vì xây dựng lại toàn bộ hệ thống lõi.

## 2.2. Trí tuệ nhân tạo và mô hình ngôn ngữ lớn

### 2.2.1. Mô hình ngôn ngữ lớn (LLM)

LLM là mô hình học sâu được huấn luyện trên khối lượng văn bản lớn, có khả năng sinh ngôn ngữ tự nhiên, tóm tắt, dịch và trả lời câu hỏi. Google Gemini là họ mô hình đa phương thức, hỗ trợ embedding và sinh văn bản, phù hợp tích hợp vào ứng dụng di động và API server [5].

**Hạn chế:** LLM có thể trả lời sai khi thiếu ngữ cảnh cụ thể hoặc khi câu hỏi nằm ngoài phạm vi kiến thức huấn luyện. Trong miền quy chế trường, sai sót thông tin có hậu quả pháp lý và học vụ.

### 2.2.2. Retrieval-Augmented Generation (RAG)

RAG kết hợp hai giai đoạn [1], [2]:

1. **Retrieval (truy hồi):** Chuyển câu hỏi thành vector embedding, tìm các đoạn văn bản (chunk) gần nhất trong kho vector (cosine similarity).
2. **Generation (sinh câu trả lời):** Đưa các chunk liên quan vào prompt, yêu cầu LLM trả lời dựa trên ngữ cảnh đó.

**Lợi ích:** Giảm hallucination, có thể trích dẫn nguồn, cập nhật tri thức bằng cách thay đổi kho tài liệu mà không fine-tune lại mô hình.

**Pipeline điển hình trong đề tài:**

```
PDF → trích xuất text → chunking (cửa sổ trượt)
    → embedding (768 chiều) → lưu vector store
    → (khi hỏi) embed query → top-k retrieval → prompt + LLM stream
```

Tham số chunk trong hệ thống: khoảng **450 ký tự**, overlap **80 ký tự**, **top-5** chunk khi truy vấn — cân bằng giữa ngữ cảnh và chi phí token.

## 2.3. Các kiến trúc hệ thống phổ biến

### 2.3.1. Kiến trúc client–server

Mô hình truyền thống: client (app) gửi yêu cầu HTTP tới server xử lý nghiệp vụ và truy cập cơ sở dữ liệu. Phù hợp RAG API và BFF cán bộ trong đề tài.

### 2.3.2. Kiến trúc ba tầng (3-tier)

- **Presentation:** Flutter app, React SPA.
- **Application:** Express BFF, FastAPI RAG.
- **Data:** Firestore, Chroma, SQLite, Storage.

Tách BFF cho cán bộ nhằm gom logic JWT, audit, FCM và proxy RAG admin — client web không truy cập trực tiếp API key nhạy cảm.

### 2.3.3. Kiến trúc Backend for Frontend (BFF)

BFF là lớp API chuyên biệt cho một loại client (ở đây là Staff Console), che giấu chi tiết Firestore Admin SDK, bcrypt, FCM và đồng nhất định dạng response [6]. Sinh viên ghi Firestore trực tiếp qua SDK với security rules — giảm độ trễ chat realtime.

### 2.3.4. Kiến trúc hướng dịch vụ và triển khai container

RAG API được đóng gói container riêng (`rag-api`), scale độc lập với `staff-console`. Docker Compose orchestrate hai service trên môi trường dev/demo [7].

## 2.4. Công nghệ và công cụ phát triển

### 2.4.1. Flutter và Dart

Flutter là framework UI đa nền tảng của Google, biên dịch sang native ARM cho Android/iOS. Đề tài dùng **Provider** quản lý state (`ChatProvider`, TTS/STT), **Material** dark theme, các package: `cloud_firestore`, `firebase_auth`, `google_generative_ai`, `sqflite`, `speech_to_text`, `flutter_tts`, `webview_flutter`.

### 2.4.2. React, Vite và Tailwind CSS

Staff Console dùng React 18 + TypeScript, Vite 5 (build nhanh), Tailwind CSS 3 (utility-first styling), `react-router-dom` v6 cho routing, `lucide-react` cho icon.

### 2.4.3. Node.js Express (BFF)

Express phục vụ REST API `/api/*`, middleware JWT, `firebase-admin`, `bcrypt`, `jsonwebtoken`, `multer` (upload proxy RAG). Production: build Vite `dist/` và `node server/index.mjs` cùng cổng 3000.

### 2.4.4. Python FastAPI và ChromaDB

FastAPI cung cấp API bất đồng bộ, endpoint SSE `/v1/chat/stream`. ChromaDB lưu embedding persistent volume `chroma-data`. Auth: `X-Student-Key`, `X-Admin-Key`.

### 2.4.5. Google Firebase

| Dịch vụ | Vai trò trong đề tài |
|---------|----------------------|
| Firestore | Chat, thông báo, đơn, góp ý, hồ sơ SV |
| Authentication | Anonymous / Google `@thanglong.edu.vn` |
| Storage | File đính kèm đơn từ |
| Cloud Messaging | Push topic `school_broadcast`, notify chat |

Security rules client-side đảm bảo sinh viên chỉ ghi thread của chính mình; `staff_accounts` deny hoàn toàn từ client.

### 2.4.6. Docker Compose

File `docker-compose.yml` định nghĩa `rag-api` (:8080) và `staff-console` (:3000), mount secret Firebase service account, biến môi trường từ `.env`.

## 2.5. Các hệ thống tương tự

### 2.5.1. Chatbot và trợ lý ảo trong giáo dục

Nhiều trường đại học triển khai chatbot FAQ trên website hoặc Facebook Messenger, thường dựa rule-based hoặc intent classification. Hạn chế: khó cập nhật khi quy chế thay đổi, không hỗ trợ câu hỏi mở phức tạp. RAG + LLM vượt trội ở câu hỏi diễn đạt tự do [3].

### 2.5.2. Ứng dụng portal sinh viên

Các app portal tích hợp điểm, lịch, thông báo nhưng ít khi tích hợp **AI tra cứu tài liệu PDF** và **chat phòng ban realtime** trong cùng một client. Đề tài hướng tới tích hợp sâu hơn.

### 2.5.3. Nền tảng hỏi đáp tài liệu (NotebookLM, các SaaS RAG)

Giải pháp thương mại cho phép upload tài liệu và hỏi đáp nhanh, nhưng không tùy biến nghiệp vụ hành chính (đơn từ, phòng ban, FCM) và không kiểm soát dữ liệu on-premise. TLU AI Assistant tự chủ stack và mô hình dữ liệu Firestore.

## 2.6. Nhận xét và định hướng giải pháp

Từ khảo sát lý thuyết và hệ thống tương tự, khóa luận định hướng:

1. **RAG làm lõi tri thức**, hỗ trợ hai mode local/server phục vụ demo và triển khai thực tế.
2. **Firestore làm nguồn sự thật** cho nghiệp vụ tương tác; vector tách riêng (Chroma/SQLite).
3. **Staff BFF bắt buộc** cho cán bộ; sinh viên realtime trực tiếp Firestore có rules.
4. **RBAC và audit** trên web cán bộ đáp ứng yêu cầu quản trị.
5. **Docker** để tái lập môi trường thí nghiệm và mở đường deploy Cloud Run.

Chương tiếp theo chuyển từ cơ sở lý thuyết sang phân tích yêu cầu và thiết kế chi tiết của TLU AI Assistant.
