# CHƯƠNG 3. PHÂN TÍCH VÀ THIẾT KẾ HỆ THỐNG

## 3.1. Mô tả quy trình nghiệp vụ

### 3.1.1. Quy trình tra cứu tri thức bằng trợ lý AI

**Tác nhân:** Sinh viên (SV).

**Luồng chính (RAG server — production):**

1. Cán bộ upload tài liệu PDF quy chế/hướng dẫn trên Staff Console (`/vectors`).
2. BFF proxy tới RAG API → ingest nền, chunk, embed → Chroma.
3. SV mở app, bật chế độ “RAG qua server” trong drawer.
4. SV nhập câu hỏi (bàn phím hoặc STT).
5. App gửi `POST /v1/chat/stream` kèm `X-Student-Key`; nhận SSE streaming.
6. App hiển thị câu trả lời; tùy chọn TTS đọc to.

**Luồng thay thế (RAG local — demo/offline):**

1. SV upload PDF trên thiết bị.
2. App trích xuất, chunk, embed vào SQLite.
3. SV hỏi đáp hoàn toàn on-device (cần `GEMINI_KEY`).

**Luồng ngoại lệ:** PDF scan không có lớp text → extract rỗng → thông báo lỗi; hết quota Gemini → thông báo và gợi ý thử lại.

### 3.1.2. Quy trình chat sinh viên – phòng ban

**Tác nhân:** Sinh viên, Cán bộ phòng ban.

1. SV chọn phòng ban từ drawer (một trong năm: `co_van`, `ct_sv`, `dao_tao`, `tai_chinh`, `tam_ly`).
2. App gọi `ensureThread` — tạo `department_threads/{studentUid}_{departmentId}` nếu chưa có.
3. SV gửi tin `senderRole: 'student'` vào subcollection `messages`.
4. Firestore cập nhật `lastMessageAt`, `preview` trên thread.
5. Cán bộ mở Staff Console `/chat`, lọc theo phòng ban, đọc thread.
6. Cán bộ trả lời qua BFF `POST .../messages` với `senderRole: 'staff'`.
7. App SV nhận realtime qua `snapshots()` — UI cập nhật ngay.

**Ràng buộc:** Mỗi SV tối đa một thread active mỗi phòng ban; threadId khớp regex `^{uid}_.+` trong security rules.

### 3.1.3. Quy trình thông báo toàn trường

1. `super_admin` tạo thông báo trên `/notifications`.
2. BFF ghi `school_notifications/{id}`.
3. BFF gửi FCM tới topic `school_broadcast`.
4. App subscribe topic; đồng thời stream Firestore hiển thị danh sách thông báo.

### 3.1.4. Quy trình nộp đơn và góp ý

**Đơn từ:**

1. SV điền form, chọn file đính kèm.
2. Upload Firebase Storage path `application_submissions/{batchId}/{file}`.
3. Ghi metadata `application_submissions` (URLs, loại đơn, timestamp).
4. Cán bộ xem read-only tại `/submissions`.

**Góp ý:**

1. SV gửi nội dung (hỗ trợ ẩn danh tùy cấu hình).
2. Ghi `feedback_letters`; cán bộ xem `/feedback`.

### 3.1.5. Sơ đồ luồng thông tin tổng quát

```
[Sinh viên] ──► Flutter App ──┬──► Firestore (chat, đơn, thông báo)
                              ├──► Storage (file đơn)
                              ├──► RAG API (SSE) ──► Chroma + Gemini
                              └──► SQLite (RAG local) + Gemini

[Cán bộ] ──► Staff Console ──► Express BFF ──┬──► Firestore Admin
                                             ├──► FCM
                                             └──► RAG API (admin)
```

## 3.2. Phân tích yêu cầu hệ thống

### 3.2.1. Yêu cầu chức năng

| Mã | Yêu cầu | Tác nhân | Ưu tiên |
|----|---------|----------|---------|
| FR-01 | Hỏi đáp tài liệu RAG (local/server) | SV | Cao |
| FR-02 | STT tiếng Việt, TTS câu trả lời | SV | Trung bình |
| FR-03 | Chat realtime với 5 phòng ban | SV, CB | Cao |
| FR-04 | Xem thông báo nhà trường + push | SV, CB | Cao |
| FR-05 | Nộp đơn có file đính kèm | SV | Cao |
| FR-06 | Gửi góp ý (ẩn danh tùy chọn) | SV | Trung bình |
| FR-07 | Mở cổng web học vụ (WebView) | SV | Thấp |
| FR-08 | Đăng nhập Firebase (anonymous/Google) | SV | Cao |
| FR-09 | Quản lý hồ sơ sinh viên | CB | Trung bình |
| FR-10 | CRUD thông báo + FCM | super_admin | Cao |
| FR-11 | Upload/xóa tài liệu RAG | CB | Cao |
| FR-12 | RBAC 3 vai trò + audit log | CB | Cao |

### 3.2.2. Yêu cầu phi chức năng

| Mã | Yêu cầu | Chỉ tiêu / ghi chú |
|----|---------|-------------------|
| NFR-01 | Thời gian phản hồi chat | Cập nhật UI < 2s sau khi ghi Firestore (mạng 4G/WiFi) |
| NFR-02 | Streaming RAG | Hiển thị token đầu tiên trong vài giây (phụ thuộc Gemini) |
| NFR-03 | Bảo mật | Rules Firestore theo ownership; API key tách student/admin/staff |
| NFR-04 | Khả dụng | Health check `/health`, `/api/public/health` |
| NFR-05 | Khả chuyển | Docker Compose; tài liệu Cloud Run |
| NFR-06 | Khả năng bảo trì | Monorepo tách `lib/`, `apps/staff-console`, `services/rag-api` |

### 3.2.3. Biểu đồ use case (tóm tắt)

**Sinh viên:** Đăng nhập; Hỏi RAG; Bật STT/TTS; Chat phòng ban; Xem thông báo; Nộp đơn; Góp ý; Mở WebView học vụ.

**Cán bộ:** Đăng nhập staff; Xem/sửa SV (super_admin); Chat trả lời; Quản lý thông báo; Xem đơn/góp ý; Quản lý vector; Xem audit; Quản lý tài khoản staff.

## 3.3. Phân tích, thiết kế chức năng nghiệp vụ

### 3.3.1. Phân rã chức năng hệ thống

```
TLU AI Assistant
├── Module Trợ lý AI
│   ├── Quản lý tài liệu (local PDF / server admin)
│   ├── Truy vấn RAG (stream)
│   └── Giọng nói (STT/TTS)
├── Module Tương tác SV–Phòng ban
│   ├── Quản lý thread chat
│   └── Tin nhắn realtime
├── Module Hành chính số
│   ├── Thông báo + FCM
│   ├── Đơn từ + Storage
│   └── Góp ý
├── Module Cổng học vụ (WebView)
└── Module Quản trị (Staff Console)
    ├── Auth JWT + RBAC
    ├── CRUD thông báo, SV, staff accounts
    ├── Proxy RAG admin
    └── Audit logs
```

### 3.3.2. Thiết kế module Trợ lý AI

**Lớp dịch vụ Flutter:**

- `PdfService`: extract text theo trang, chunk sliding window.
- `EmbeddingService`: `embedBatch` / `embed` qua Gemini embedding (768 dims).
- `VectorStore`: SQLite, cosine top-5.
- `LocalRagService`: `queryStream()` — prompt + Gemini Flash stream.
- `RemoteRagService`: HTTP SSE tới `/v1/chat/stream`.

**Lớp RAG API (Python):**

- Ingest PDF: parse, chunk, embed, upsert Chroma.
- Chat: retrieve top-k → build prompt → stream Gemini response.
- Auth middleware: kiểm tra `X-Student-Key` / `X-Admin-Key`.

**ChatProvider:** Giữ lịch sử hội thoại AI **in-memory** (không persist Firestore) — phân tách rõ chat AI và chat phòng ban.

## 3.4. Phân tích, thiết kế kiến trúc hệ thống

### 3.4.1. Kiến trúc logic phân tầng

| Tầng | Thành phần | Trách nhiệm |
|------|------------|-------------|
| Presentation | Flutter, React SPA | UI/UX, validation cơ bản |
| Application | Express BFF, FastAPI | Nghiệp vụ, auth, orchestration |
| Data | Firestore, Chroma, SQLite, Storage | Lưu trữ bền vững |
| External | Gemini API, FCM | AI và push |

### 3.4.2. Sơ đồ triển khai (Docker dev)

| Dịch vụ | Cổng | Ghi chú |
|---------|------|---------|
| `rag-api` | 8080 | Emulator Android: `10.0.2.2:8080` |
| `staff-console` | 3000 | UI + API cùng origin |
| Vite dev (tùy chọn) | 5174 | Proxy `/api` → 3001 |

### 3.4.3. Sequence diagram — Đăng nhập cán bộ

```
React UI → POST /api/auth/staff-login → BFF
BFF → Firestore staff_accounts → bcrypt verify
BFF → JWT 12h + profile → localStorage
Các request sau: Authorization: Bearer <token>
```

### 3.4.4. Sequence diagram — Chat phòng ban

```
Flutter → Firestore: create message (student)
Staff Web → BFF GET threads/messages
Staff Web → BFF POST reply (staff)
BFF → Firestore Admin: write message
Flutter ← snapshots: UI update
```

### 3.4.5. Phân quyền RBAC (Staff Console)

| Vai trò | Mã | Quyền điển hình |
|---------|-----|-----------------|
| Quản trị hệ thống | `super_admin` | Toàn quyền + CRUD staff + thông báo + sửa SV |
| Cán bộ | `staff` | SV (xem), chat, đơn, góp ý, vector, settings |
| Giám sát | `auditor` | SV (xem), thông báo (xem), audit |

Logic client: `staffRole.ts`; logic server: middleware trong `server/index.mjs`.

## 3.5. Phân tích, thiết kế cơ sở dữ liệu

### 3.5.1. Mô hình quan hệ logic (Firestore)

**Thực thể chính:**

- `users/{uid}` — hồ sơ SV, `fcmToken`, metadata.
- `departments/{id}` — danh mục 5 phòng ban (read-only client).
- `department_threads/{threadId}` — metadata chat, `threadId = {studentUid}_{departmentId}`.
- `department_threads/{id}/messages/{msgId}` — nội dung tin nhắn.
- `school_notifications/{id}` — thông báo.
- `application_submissions/{id}` — đơn + `attachments[]`.
- `feedback_letters/{id}` — góp ý.
- `staff_accounts/{id}` — login cán bộ (hash password) — **chỉ BFF**.
- `audit_logs/{id}` — append-only từ BFF.

**Không lưu trên Firestore:** Vector embedding RAG (Chroma/SQLite); lịch sử chat AI Gemini.

### 3.5.2. Thiết kế logic — collection `department_threads`

| Trường | Kiểu | Mô tả |
|--------|------|-------|
| studentUid | string | UID Firebase của SV |
| departmentId | string | Một trong 5 ID phòng ban |
| departmentTitle | string | Tên hiển thị |
| status | string | Trạng thái thread (open/closed…) |
| preview | string | Tin nhắn xem trước |
| createdAt | timestamp | Thời điểm tạo |
| lastMessageAt | timestamp | Phục vụ sort |

**Subcollection `messages`:**

| Trường | Mô tả |
|--------|-------|
| senderRole | `student` \| `staff` |
| text | Nội dung |
| createdAt | timestamp |

### 3.5.3. Thiết kế vật lý — Chroma và SQLite

- **Chroma:** collection persistent, metadata document id, filename; volume Docker `chroma-data`.
- **SQLite (Flutter):** bảng chunk + embedding blob/JSON; index cosine trong application layer.

### 3.5.4. Security Rules — nguyên tắc thiết kế

- `isStudentLike()`: email `@thanglong.edu.vn` **hoặc** anonymous (demo).
- `ownsThreadId(threadId)`: thread phải bắt đầu bằng `auth.uid`.
- SV không sửa `role`, `permissions` trên `users`.
- `staff_accounts`: `allow read, write: if false` — mọi thao tác qua Admin SDK.
- Index composite: `departmentId` + `lastMessageAt` cho truy vấn chat cán bộ.

### 3.5.5. Storage Rules

Path `application_submissions/{batchId}/{file}` — chỉ SV sở hữu batch được ghi; cán bộ đọc qua Admin SDK trên BFF.

## 3.6. Phân tích, thiết kế giao diện

### 3.6.1. Ứng dụng Flutter — nguyên tắc UX

- **Dark theme** thống nhất, font Google Fonts, markdown cho câu trả lời AI.
- **HomeScreen:** khung chat AI trung tâm; drawer điều hướng feature.
- **Drawer:** toggle RAG local/server; danh sách phòng ban; thông báo; đơn; góp ý; WebView học vụ.
- **Input bar:** nút mic (STT), gửi, indicator streaming/waveform khi TTS.

### 3.6.2. Màn hình tiêu biểu

| Màn hình | File tham chiếu | Chức năng |
|----------|-----------------|-----------|
| Trang chủ / Chat AI | `home_screen.dart` | Hỏi đáp RAG |
| Chat phòng ban | `department_chat_screen.dart` | Thread realtime |
| Thông báo | `notifications_screen.dart` | Stream `school_notifications` |
| Đơn từ | `application_form_screen.dart` | Upload Storage |
| Góp ý | `feedback_letter_screen.dart` | Ghi `feedback_letters` |
| Auth gate | `firebase_auth_gate.dart` | Anonymous / Google |

**Chế độ demo:** `DemoReportConfig.enabled` — dữ liệu giả, tắt Firebase cho screenshot báo cáo.

### 3.6.3. Staff Console — cấu trúc layout

- **AppLayout:** sidebar navigation theo route.
- **LoginPage:** `loginId`/email + password.
- **DashboardHome:** health check tổng quan.
- **DepartmentChatPage:** danh sách thread + khung chat.
- **VectorDocsPage:** upload PDF, theo dõi ingest job.
- **AuditLogsPage:** bảng thao tác (read-only).

Thiết kế Tailwind: bảng dữ liệu, modal xác nhận, toast lỗi API.

### 3.6.4. Thiết kế API BFF (tóm tắt)

| Nhóm | Endpoint |
|------|----------|
| Auth | `POST /api/auth/staff-login`, `GET /api/auth/me` |
| Health | `GET /api/public/health` |
| Users | `GET /api/users`, `PATCH /api/users/:uid` |
| Notifications | `GET/POST/DELETE /api/notifications` |
| Submissions / Feedback | `GET /api/submissions`, `GET /api/feedback` |
| Chat | `GET /api/chat/threads`, `GET/POST .../messages` |
| Staff | `GET/POST/PATCH/DELETE /api/staff/accounts` |
| RAG proxy | `GET/POST/DELETE /api/rag/documents`, `GET /api/rag/ingest-jobs/:id` |
| Audit | `GET /api/audit-logs` |

Bypass vận hành: header `X-Staff-Key` = `STAFF_API_KEY` (không dùng production công khai).

## 3.7. Thiết kế bảo mật

1. **Tách phạm vi auth:** SV (Firebase token) ≠ CB (JWT riêng).
2. **Không lộ hash mật khẩu cán bộ** ra client SDK.
3. **API keys** (`STUDENT_API_KEY`, `ADMIN_API_KEY`, `GEMINI_API_KEY`) qua biến môi trường, không commit.
4. **Audit** cho thao tác: xóa vector, sửa SV, tạo staff, phát thông báo.
5. **Hướng production:** bắt buộc Google Sign-In `@thanglong.edu.vn`, tắt `kBypassAuthGate` và `DemoReportConfig`.

Chương 4 trình bày hiện thực hóa các thiết kế trên và kết quả kiểm thử.
