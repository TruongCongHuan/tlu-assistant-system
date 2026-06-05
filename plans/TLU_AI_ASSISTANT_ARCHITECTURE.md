# Kiến Trúc Hệ Thống: TLU AI Assistant (Zero-cost Scale RAG)

**Vai trò:** Principal System Architect  
**Mục tiêu:** Tối ưu Cost-to-Performance, kiến trúc tinh gọn, tuyệt đối không thỏa hiệp về Technical Quality. Portability là tối thượng (Docker First).

---

## Phần 1: Thiết Kế 3 Phương Án High-Level & Low-Level Architecture

### 1. The Budget King (Chiến binh sinh tồn)
*Mục tiêu:* Tối ưu triệt để Free Tier GCP (Cloud Run, Cloud Storage) và các dịch vụ thứ ba. Duy trì chi phí bằng 0 sau khi hết 300 USD.
*   **Compute:** Cloud Run (Scale to zero), RAM 512MB, vCPU 1. Tận dụng 2 triệu request miễn phí/tháng.
*   **Vector DB:** ChromaDB chạy nhúng trực tiếp trên bộ nhớ Cloud Run (in-memory hoặc ephemeral disk) + backup/sync vector định kỳ ra Cloud Storage (GCS) thay vì Persistent Disk tốn phí. Khi cold start, download file vector từ GCS nạp vào ChromaDB.
*   **LLM:** Gemini Flash Free Tier (15 RPM, 1M TPM).
*   **Trade-off:** Latency cao ở lần cold start đầu tiên do phải kéo data từ GCS.

### 2. The Professional Performance (Max Performance - 90 Days Sprint)
*Mục tiêu:* Đốt cháy 300 USD trong 90 ngày tập trung vào UX mượt mà, độ trễ cực thấp, High Availability. Thu thập dữ liệu sử dụng thực tế của sinh viên.
*   **Compute:** Cloud Run (Min instances = 1 để chống cold start hoàn toàn). RAM 2GB, vCPU 2.
*   **Vector DB:** ChromaDB host riêng trên một VM Compute Engine (e2-micro/small) đính kèm Persistent Disk (SSD) hoặc dùng Cloud SQL (pgvector) để query siêu tốc.
*   **LLM:** Cụm proxy gọi Gemini Flash/Pro (trả phí API nếu cần để phá bỏ rate limit 15 RPM).
*   **Trade-off:** Sau 90 ngày, nếu không downgrade hệ thống sẽ đốt sạch tiền túi.

### 3. The Portable Container (Docker-Native & Hybrid)
*Mục tiêu:* Chống Vendor Lock-in tuyệt đối. Chạy mượt trên Cloud Run hiện tại và dễ dàng bê nguyên vẹn về local server của trường (Self-hosted bằng Docker Swarm/k3s).
*   **Kiến trúc:** Phân tách rõ ràng Stateless Backend (API Gateway + RAG Logic) và Stateful DB (ChromaDB). Đóng gói toàn bộ bằng `docker-compose.yml`.
*   **Deploy Cloud:** Backend đẩy lên Cloud Run. ChromaDB đẩy lên Compute Engine VM gắn Volume riêng biệt.
*   **Deploy Local (Sau này):** `docker-compose up -d` hoặc apply Helm chart trên server trường. Mọi thứ hoạt động y hệt.
*   **Trade-off:** DevOps overhead cao hơn ở việc cấu hình kết nối mạng nội bộ giữa Cloud Run và VM.

---

## Phần 2: Đi Sâu Vào Chi Tiết Kỹ Thuật (Low-Level Design)

### Stack Selection & Quyết Định Kiến Trúc
*   **Tại sao Cloud Run là chân ái thay vì Cloud Functions?** Cloud Functions giam cầm code bằng ecosystem của Google (Vendor Lock-in). Cloud Run chạy **bất kỳ Docker container nào**. Điều này thỏa mãn yêu cầu sinh viên khóa sau có thể tự build image và chạy trên máy cá nhân mà không cần giả lập môi trường GCP. Hỗ trợ websockets, request timeout dài hơn (lên đến 60 phút).
*   **Storage cho ChromaDB (Persistent Disk vs Stateful workloads):** Serverless (Cloud Run) sinh ra không dành cho Stateful workloads. Nếu nhét ChromaDB vào Cloud Run, file sqlite của ChromaDB sẽ bị xóa mỗi khi scale to zero. 
    * *Giải pháp thực dụng:* Lưu database Chroma ra file cục bộ, nén lại, đẩy lên Cloud Storage (GCS). Mỗi khi Cloud Run cold start, nó kéo file này từ GCS xuống container (`/tmp`), giải nén và start ChromaDB in-memory. GCS rẻ hơn rất nhiều so với Persistent Disk chạy 24/7.

### RAG Pipeline: Tối Ưu I/O Bottleneck
*   **Vấn đề:** Lấy embedding, gọi LLM, query VectorDB là I/O bound. Gọi tuần tự sẽ tăng P99 Latency.
*   **Chiến lược:** 
    1. Trả ngay câu trả lời mẫu/cache (Redis - nếu có) trong khi chạy nền.
    2. Nếu cache miss: Chuyển sang SSE (Server-Sent Events) để stream text về Flutter UI ngay khi LLM có token đầu tiên, thay vì chờ LLM gen xong toàn bộ. Flutter UI sẽ hiển thị chữ "nhảy nhảy" như ChatGPT, che lấp hoàn toàn độ trễ I/O của Vector Search.

### Credit Allocation Strategy (Phân Bổ 300 USD / 90 ngày)
*   **Compute (Cloud Run):** $30/tháng (giữ 1 min instance giờ cao điểm, scale to zero ban đêm).
*   **Vector Storage (VM + Disk - Nếu dùng phương án 2):** $20/tháng (e2-micro + 20GB Standard Persistent Disk).
*   **Cloud Logging/Monitoring:** $10/tháng (giới hạn log retention ở 7 ngày).
*   **LLM API Overages:** Dự phòng $40/tháng cho các đợt spike traffic lúc ôn thi.
*   *Phòng thủ cháy túi:* Setup **Cloud Billing Budgets & Alerts**, trigger webhook tắt ngay lập tức các dịch vụ nếu chạm mốc $90/tháng, chặn API abuse.

### System Resilience & Security: 3 Câu Hỏi Phản Biện Sắc Bén

1.  **Nếu Gemini Flash API sập hoặc rate limit quá gắt (429 Too Many Requests), hệ thống sẽ chết đứng?**
    *   *Giải quyết:* Triển khai API Circuit Breaker và Fallback Model. Nếu Gemini lỗi liên tục 3 lần, tự động chuyển hướng request sang Groq (Llama 3) free tier dự phòng. Flutter UI hiển thị cảnh báo "Hệ thống đang quá tải, tốc độ có thể chậm hơn".
2.  **Làm sao để sinh viên không viết script spam API đốt sạch credit?**
    *   *Giải quyết:* Không bao giờ mở public API. Bắt buộc có token Firebase Auth. Backend implement Rate Limiter (Redis hoặc in-memory hash map) theo UID sinh viên: Max 10 queries/phút, 100 queries/ngày. Vượt ngưỡng -> HTTP 429.
3.  **Dữ liệu RAG có chứa tài liệu nội bộ, làm sao để ChromaDB file trên GCS không bị lộ?**
    *   *Giải quyết:* Bucket GCS phải Private (chỉ Service Account của Cloud Run mới được IAM cấp quyền đọc). Mọi truy cập vào hệ thống phải qua JWT verification của Backend, ChromaDB tuyệt đối không expose port ra internet.

---

## Phần 3: Giải Quyết 4 Bài Toán "Hardcore" Của Hệ Thống

### 1. Cold Start Mitigation (Container "Ngủ Đông")
Cloud Run mất 3-5 giây để init container.
*   **Kỹ thuật Lazy-loading UI & Pre-warming:** 
    Khi sinh viên vừa mở app Flutter, app lập tức gửi một request HTTP siêu nhẹ (`/ping`) ẩn dưới nền. Request này đánh thức Cloud Run. Trong lúc sinh viên loay hoay gõ câu hỏi (mất 5-10 giây), container đã "ấm" (warmed up). Khi user nhấn Submit, container đã sẵn sàng xử lý, latency về lại mức vài chục ms.

### 2. Graceful Downgrade Path (Sau 90 ngày)
Về đích Free Tier không sụp đổ.
*   **Chiến lược:** Loại bỏ min-instances (chấp nhận cold start trở lại). Chuyển hoàn toàn ChromaDB từ VM/Persistent Disk sang kiến trúc "The Budget King" (GCS pull/push). Việc này chỉ cần sửa đúng 1 dòng trong `docker-compose` và cập nhật env var của Cloud Run. Code core RAG giữ nguyên 100%.

### 3. GCP Serverless vs Free PaaS (Vercel/Render)
*   **Execution Timeout:** Vercel Free có giới hạn timeout tàn bạo (10-15s). RAG Pipeline (Embedding + Search + LLM Generation) rất dễ vượt qua mức này, trả về lỗi 504 Gateway Timeout. Cloud Run cho phép timeout lên tới 60 phút.
*   **Quotas & Tầm nhìn:** Render/Vercel free tier sleep/wake rất chậm và dễ bị ban nếu lạm dụng. GCP cấp cho Cloud Run quota 2 triệu requests/tháng vĩnh viễn, đủ chịu tải 10,000 sinh viên. Docker trên Cloud Run đảm bảo khi quy mô phình to, mang thẳng file Docker đó cắm vào máy chủ của trường -> Run. Vercel không thể làm điều này.

### 4. Scientific Contribution: Đánh Giá Custom RAG vs Vertex AI Search
*   **Vertex AI Search:** Hoạt động như một "Black box", chi phí đắt đỏ ($3/1000 queries), index tính tiền riêng. Phù hợp doanh nghiệp giàu có.
*   **Luận điểm bảo vệ đồ án:** TLU AI Assistant chứng minh được rằng việc tự build **Custom RAG (Docker + ChromaDB + Gemini Flash Free)** kết hợp với kỹ thuật Chunking thông minh (Semantic split) và Prompt Engineering có thể đạt độ chính xác (Relevance Score) tiệm cận Vertex AI ở các use-cases tài liệu văn bản thông thường, nhưng với chi phí vận hành giảm đi >95%. Đây là đóng góp khoa học về tính thực tiễn (Practicality) và tối ưu chi phí (Cost-Efficiency) trong kỹ thuật phần mềm, đập tan định kiến RAG là tốn kém.

---

## Phần 4: Ma Trận So Sánh Quyết Định

| Metrics | Phương án 1: The Budget King | Phương án 2: Professional Perf. | Phương án 3: Portable Hybrid |
| :--- | :--- | :--- | :--- |
| **Kiến Trúc Tóm Tắt** | Cloud Run (0 min) + Chroma GCS | Cloud Run (1 min) + Chroma VM | Cloud Run + Self-hosted VM/Server |
| **End-to-End Latency** | Cao (Cold Start: 3-6s). Nhanh sau đó | Cực thấp (ổn định < 1s) | Thấp đến Cực thấp (Tùy server) |
| **Maintenance Effort (DevOps)**| Thấp (Serverless lo 100%) | Trung bình (Quản lý thêm 1 VM) | Cao (Phải cấu hình network nội bộ) |
| **Scalability (10k Users)** | Xuất sắc (Scale tự động, không rớt mạng) | Tốt (Phải scale cả VM thủ công) | Tốt (Scale dựa trên Swarm/k8s) |
| **Estimated Cost (Post-Credit)** | **$0/tháng** (Nằm trong Free Tier) | ~$40 - $60/tháng (Tiền VM + IP) | Tiền điện server trường (Tự host) |

**Quyết định của System Architect:** 
Trong giai đoạn đầu 90 ngày, triển khai **Phương án 3 (Portable Hybrid)** nhưng host trên GCP để tận dụng Credit, lấy UX tốt nhất thuyết phục nhà trường. 
Tuần thứ 10 (chuẩn bị hết tiền), trigger **Graceful Downgrade** chuyển mượt mà hệ thống sang **Phương án 1 (The Budget King)** để chạy duy trì. Nếu trường duyệt cấp ngân sách hoặc server, bê nguyên kiến trúc Container về cắm chạy nội bộ.