# Kiểm thử end-to-end (RAG + Web cán bộ + App sinh viên)

## Chuẩn bị

1. Copy `.env.example` → `.env` ở thư mục gốc, điền `GEMINI_API_KEY`. Demo tối nay: `STORAGE_BACKEND=file` (mặc định trong compose).
2. `docker compose up --build` — RAG API `http://127.0.0.1:8080`, **web cán bộ** `http://127.0.0.1:3000`.
3. Đăng nhập cán bộ: `super_admin` / `123456` (file storage). Hoặc **Cài đặt** → Staff API key nếu dùng master key.
4. Chi tiết quay demo: [DEMO_TONIGHT.md](DEMO_TONIGHT.md).

**Lỗi 429 khi upload (RESOURCE_EXHAUSTED):** không phải “key hết hạn”, mà là **hết quota / vượt RPM** của gói miễn phí — mỗi chunk = 1 lần gọi `embedContent`. Giảm: file `.md` rất ngắn để test; trong `.env` tăng `EMBED_REQUEST_DELAY_MS` (mặc định 400); `docker compose up --build` lại. Xem [Gemini rate limits](https://ai.google.dev/gemini-api/docs/rate-limits).

## Luồng E2E

1. **Web cán bộ:** mục **Vector & tài liệu RAG** → upload `.md` hoặc `.pdf` nhỏ → chờ job **completed** → bảng tài liệu có dòng mới.
2. **App Flutter** (điện thoại thật — IP LAN Mac):
   ```bash
   flutter run \
     --dart-define=BFF_BASE_URL=http://192.168.1.42:3000 \
     --dart-define=API_BASE_URL=http://192.168.1.42:8080 \
     --dart-define=STUDENT_API_KEY=dev-student-key \
     --dart-define=GEMINI_KEY=YOUR_GEMINI_KEY
   ```
   - Android emulator: `10.0.2.2` thay `127.0.0.1`.
3. Chat phòng ban SV ↔ cán bộ (polling JSON, không Firebase). Sinh viên seed: `demo_student_257480001`.
4. Mở drawer → bật **RAG qua server** → chat một câu liên quan nội dung file vừa upload → nhận câu trả lời có nguồn / hợp lý.

## Smoke (API)

```bash
curl -sS http://127.0.0.1:8080/health
curl -sS -N -H "X-Student-Key: dev-student-key" -H "Content-Type: application/json" \
  -d '{"question":"Xin chào"}' http://127.0.0.1:8080/v1/chat/stream | head
```

## Video dự phòng

Quay màn hình toàn bộ luồng (web cán bộ upload → app chat) **trước ngày bảo vệ**; lưu file `.mp4` ngoài máy phòng sự cố mạng.
