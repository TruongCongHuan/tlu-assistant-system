# Quay demo tối nay (local JSON + Docker)

## 1. Chuẩn bị

```bash
cp .env.example .env   # điền GEMINI_API_KEY
ipconfig getifaddr en0  # ghi IP LAN, ví dụ 192.168.1.42
docker compose up --build
```

- Staff console: http://127.0.0.1:3000 — đăng nhập `super_admin` / `123456`
- RAG API: http://127.0.0.1:8080

## 2. Flutter (điện thoại thật, cùng Wi‑Fi Mac)

```bash
flutter run \
  --dart-define=BFF_BASE_URL=http://192.168.51.101:3000 \
  --dart-define=STUDENT_API_KEY=dev-student-key \
  --dart-define=API_BASE_URL=http://192.168.51.101:8080 \
  --dart-define=GEMINI_KEY=AIzaSyCUdvncX2Qqh5baWN7VULb-nrFr7AsGMok
```

Đổi `192.168.1.42` bằng IP thật của Mac.

## 3. Smoke API

```bash
curl -sS http://127.0.0.1:3000/api/public/health
curl -sS http://127.0.0.1:8080/health

curl -sS -H "X-Student-Key: dev-student-key" \
  http://127.0.0.1:3000/api/student/notifications

curl -sS -X POST -H "X-Student-Key: dev-student-key" \
  -H "Content-Type: application/json" \
  -d '{"login":"super_admin","password":"123456"}' \
  http://127.0.0.1:3000/api/auth/staff-login
```

## 4. Kịch bản quay (7 bước)

1. Mac: Staff → Vector & tài liệu → upload `.md` ngắn → job completed
2. ĐT: App → RAG server → hỏi nội dung file
3. ĐT: Chat Phòng Đào tạo → Mac Staff Chat → reply → ĐT thấy tin ~1s
4. Mac: Thông báo → tạo mới → ĐT snackbar
5. ĐT: Đơn từ + PDF → Mac Submissions
6. ĐT: Góp ý → Mac Feedback
7. Mac: Finder `./data/chats/`, `./data/rag/sources/`

## 5. Sau khi sửa lỗi (rebuild bắt buộc)

```bash
docker compose up --build -d
```

- **RAG:** upload dùng `FormData` native (Node 20) — rebuild `staff-console`.
- **Chat CB:** 3 cột Phòng ban → SV → tin nhắn; tự refresh 2s; popup góc phải khi có tin mới.
- **App SV:** badge chuông + drawer phòng ban; tiếng + snackbar khi cán bộ trả lời.
- **Đơn từ:** Staff bấm tên file để tải về.

## 6. Mai bật lại Firebase

- `lib/config/app_runtime_config.dart` → `AppBackend.firebase`
- `.env` → `STORAGE_BACKEND=firebase` + mount `secrets/firebase-sa.json`
