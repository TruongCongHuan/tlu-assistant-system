# CHƯƠNG 4. TRIỂN KHAI HỆ THỐNG VÀ THỰC NGHIỆM

## 4.1. Môi trường phát triển

### 4.1.1. Phần cứng và hệ điều hành

- Máy phát triển: macOS / Windows / Linux (đa nền tảng Flutter).
- Thiết bị thử nghiệm: Android Emulator (API 30+), thiết bị thật Android 11+; iOS Simulator / thiết bị (macOS + Xcode 15+ khi build iOS).

### 4.1.2. Phần mềm và công cụ

| Thành phần | Phiên bản / công cụ |
|------------|---------------------|
| Flutter SDK | 3.x (theo `pubspec.yaml` dự án) |
| Dart | Kèm Flutter |
| Node.js | 20 LTS (staff-console, Docker image) |
| Python | 3.10+ (rag-api) |
| Docker & Docker Compose | Orchestrate `rag-api`, `staff-console` |
| Firebase CLI | Deploy rules, indexes |
| IDE | VS Code / Android Studio / Cursor |

### 4.1.3. Tài khoản và khóa dịch vụ

- **Google AI Studio:** `GEMINI_API_KEY` — embedding + generate.
- **Firebase project:** Firestore, Auth, Storage, FCM; service account JSON cho BFF.
- **Biến môi trường:** sao chép từ `.env.example` → `.env` (không commit secrets).

## 4.2. Cài đặt và triển khai hệ thống

### 4.2.1. Cấu trúc monorepo

```
Graduation_Thesis/
├── lib/                      # Flutter app (tlu_ai_assistant)
├── apps/staff-console/       # React + Express BFF
├── services/rag-api/         # FastAPI + Chroma
├── docker-compose.yml
├── firestore.rules
├── firestore.indexes.json
├── storage.rules
└── docs/                     # E2E, Cloud Run
```

### 4.2.2. Triển khai backend bằng Docker Compose

```bash
cp .env.example .env
# Điền GEMINI_API_KEY, STUDENT_API_KEY, ADMIN_API_KEY, STAFF_API_KEY
# Mount secrets/firebase-sa.json cho staff-console
docker compose up --build
```

Kết quả:

- RAG API: `http://127.0.0.1:8080/health`
- Staff Console: `http://127.0.0.1:3000` — UI + `/api/*`

### 4.2.3. Triển khai Staff Console chế độ dev

```bash
cd apps/staff-console
npm install
npm run dev
```

- Vite: `http://localhost:5174`
- Express BFF: cổng `3001`, proxy `/api` từ Vite.

Tài khoản bootstrap (khi Firestore trống): `super_admin` / `123456`.

### 4.2.4. Cài đặt ứng dụng Flutter

```bash
flutter pub get
flutter run \
  --dart-define=GEMINI_KEY=<GEMINI_API_KEY> \
  --dart-define=API_BASE_URL=http://10.0.2.2:8080 \
  --dart-define=STUDENT_API_KEY=dev-student-key
```

- Emulator Android dùng `10.0.2.2` thay cho `localhost` máy host.
- Bật “RAG qua server” trong drawer khi test server mode.

Build release APK:

```bash
flutter build apk --release --dart-define=GEMINI_KEY=...
```

### 4.2.5. Cấu hình Firebase

1. Tạo project Firebase, bật Auth (Anonymous, Google), Firestore, Storage, FCM.
2. Deploy rules:

```bash
firebase deploy --only firestore:rules,firestore:indexes,storage
```

3. Flutter: `flutterfire configure` → `lib/firebase_options.dart`.
4. BFF: `FIREBASE_SERVICE_ACCOUNT_JSON` hoặc mount `GOOGLE_APPLICATION_CREDENTIALS`.

### 4.2.6. Hiện thực các module tiêu biểu

**RAG local (`local_rag_service.dart`):**

1. `PdfService.extractText()` — `syncfusion_flutter_pdf`.
2. `PdfService.chunk()` — 450 ký tự, overlap 80.
3. `EmbeddingService.embedBatch()` — Gemini `text-embedding-004`, 768 chiều.
4. `VectorStore.insertChunks()` — SQLite.
5. `queryStream()` — embed query, cosine top-5, prompt + Gemini Flash stream.

**RAG remote (`remote_rag_service.dart`):**

- HTTP client đọc SSE từ `POST /v1/chat/stream`.
- Header `X-Student-Key` từ `api_config.dart`.

**Chat phòng ban (`department_chat_repository.dart`):**

- `ensureThread(studentUid, departmentId, title)`
- `sendMessage(threadId, text, senderRole)`
- `watchMessages(threadId)` → `Stream` Firestore snapshots.

**BFF (`server/index.mjs` ~1060 dòng):**

- Khởi tạo `firebase-admin`, middleware JWT, route map theo RBAC.
- Proxy multipart upload sang RAG admin ingest.
- `messaging.send` topic `school_broadcast`.

**RAG API (`services/rag-api/app/main.py`):**

- Endpoints admin: documents CRUD, ingest job status.
- Endpoint student: chat stream SSE.

## 4.3. Kiểm thử hệ thống

### 4.3.1. Chiến lược kiểm thử

| Cấp độ | Phạm vi | Công cụ / phương pháp |
|--------|---------|------------------------|
| Unit | Hàm chunk, parse threadId | Test thủ công / Dart test (mở rộng) |
| Integration | BFF + Firestore, RAG ingest | Postman, curl, checklist E2E |
| System | Luồng SV ↔ CB end-to-end | Thiết bị thật + emulator |
| Chấp nhận | FR/NFR đã liệt kê Chương 3 | Kịch bản demo |

### 4.3.2. Kịch bản kiểm thử chức năng

| ID | Kịch bản | Bước thực hiện | Kết quả mong đợi |
|----|----------|----------------|------------------|
| TC-01 | Health backend | `GET /health`, `GET /api/public/health` | HTTP 200 |
| TC-02 | Đăng nhập cán bộ | Login `super_admin` | JWT + redirect dashboard |
| TC-03 | Upload vector | PDF trên `/vectors` | Job ingest completed, list documents |
| TC-04 | RAG server SV | Hỏi quy chế trên app (server mode) | Stream câu trả lời có ngữ cảnh |
| TC-05 | RAG local | Upload PDF on-device, hỏi | Trả lời từ SQLite retrieval |
| TC-06 | Chat SV → CB | SV gửi tin; CB trả lời | Realtime hai phía |
| TC-07 | Thông báo | Tạo notification + FCM | SV nhận push + thấy trên app |
| TC-08 | Nộp đơn | Upload file + submit | Hiển thị trên `/submissions` |
| TC-09 | RBAC auditor | Đăng nhập auditor | Không truy cập route cấm |
| TC-10 | Demo mode | `DemoReportConfig.enabled=true` | UI chạy không Firebase |

Checklist chi tiết: `docs/E2E_CHECKLIST.md` trong repository.

### 4.3.3. Kiểm thử phi chức năng

- **Bảo mật:** Thử ghi threadId không thuộc `uid` → Firestore permission denied.
- **Hiệu năng:** Đo thời gian first token SSE (phụ thuộc mạng và Gemini); chat snapshot < 2s trên WiFi.
- **Ổn định:** Restart container `rag-api` — ingest jobs in-memory mất (ghi nhận hạn chế).

### 4.3.4. Lỗi thường gặp và xử lý

| Triệu chứng | Nguyên nhân | Cách xử lý |
|-------------|-------------|------------|
| RAG không trả lời | Sai `API_BASE_URL` / thiếu `STUDENT_API_KEY` | Kiểm tra dart-define và `.env` |
| Firestore permission | Chưa auth / sai threadId | Anonymous sign-in; đúng format `{uid}_{dept}` |
| Upload đơn lỗi | Storage rules | Deploy `storage.rules`, đúng path |
| Staff login fail | Chưa seed account | Bootstrap `super_admin` hoặc tạo qua API |

## 4.4. Đánh giá hệ thống

### 4.4.1. Đánh giá mức độ đáp ứng yêu cầu

| Yêu cầu | Đánh giá | Ghi chú |
|---------|----------|---------|
| FR-01 RAG | Đạt | Hai chế độ local + server |
| FR-03 Chat phòng ban | Đạt | 5 phòng ban, realtime |
| FR-04 Thông báo FCM | Đạt | Topic broadcast |
| FR-05 Đơn từ | Đạt | Storage + metadata |
| FR-11 Vector admin | Đạt | Qua BFF proxy |
| FR-12 RBAC + audit | Đạt | 3 role, `audit_logs` |
| NFR-03 Bảo mật | Đạt một phần | Cần bật auth email trường production |
| NFR-05 Triển khai | Đạt | Docker + tài liệu Cloud Run |

### 4.4.2. Ưu điểm

- Tích hợp **AI + hành chính số** trong một sản phẩm thống nhất.
- **Realtime** chat Firestore không cần polling.
- **Tách vector store** khỏi Firestore — mô hình rõ ràng.
- **Monorepo** dễ bảo trì và demo cho hội đồng.

### 4.4.3. Hạn chế trong thực nghiệm

- Xác thực SV chủ yếu anonymous/demo; Google `@thanglong.edu.vn` chưa bắt buộc.
- Job ingest RAG in-memory — không durable khi restart.
- Chưa có bộ unit test tự động đầy đủ; kiểm thử thủ công chiếm tỷ lệ lớn.
- Phụ thuộc quota Gemini free tier; PDF scan chất lượng thấp không extract được text.
- Hội thoại AI không lưu lịch sử lâu dài — chưa đáp ứng nhu cầu “xem lại lịch sử học vụ” đa thiết bị.

### 4.4.4. So sánh RAG local và server

| Tiêu chí | Local (SQLite) | Server (Chroma) |
|----------|----------------|-----------------|
| Quản lý tài liệu | SV tự upload | Cán bộ tập trung |
| Offline | Có thể hỏi sau khi index | Cần mạng |
| Đồng bộ tri thức | Khó đồng nhất toàn trường | Đồng nhất qua ingest |
| Bảo mật | Dữ liệu trên máy SV | Kiểm soát server |
| Phù hợp | Demo, thử nghiệm | Production scale |

Kết quả chương này là prototype chạy được end-to-end, làm cơ sở cho Chương 5 tổng kết và hướng phát triển.
