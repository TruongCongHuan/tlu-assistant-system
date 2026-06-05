# PHỤ LỤC

## PHỤ LỤC 1. DANH MỤC PHÒNG BAN VÀ MÃ ĐỊNH DANH

| STT | Mã (`departmentId`) | Tên phòng ban |
|-----|---------------------|---------------|
| 1 | `co_van` | Cố vấn học tập |
| 2 | `ct_sv` | Phòng Công tác Chính trị Sinh viên |
| 3 | `dao_tao` | Phòng Đào tạo |
| 4 | `tai_chinh` | Phòng Tài chính - Kế toán |
| 5 | `tam_ly` | Phòng Tham vấn tâm lý |

*Nguồn: `lib/config/department_catalog.dart` trong mã nguồn dự án.*

---

## PHỤ LỤC 2. BIẾN MÔI TRƯỜNG MẪU (`.env.example`)

| Biến | Mô tả |
|------|-------|
| `GEMINI_API_KEY` | Khóa Google Gemini (embedding + generate) |
| `STUDENT_API_KEY` | Khóa xác thực sinh viên gọi RAG API |
| `ADMIN_API_KEY` | Khóa quản trị ingest tài liệu RAG |
| `STAFF_API_KEY` | Khóa bypass vận hành BFF (không public) |
| `JWT_SECRET` | Secret ký JWT cán bộ |
| `FIREBASE_SERVICE_ACCOUNT_JSON` | JSON service account (hoặc mount file) |

Flutter (`--dart-define`):

| Biến | Mô tả |
|------|-------|
| `GEMINI_KEY` | Gemini cho RAG on-device |
| `API_BASE_URL` | URL RAG API (vd. `http://10.0.2.2:8080`) |
| `STUDENT_API_KEY` | Header `X-Student-Key` |

---

## PHỤ LỤC 3. ENDPOINT RAG API (TÓM TẮT)

| Phương thức | Đường dẫn | Xác thực |
|-------------|-----------|----------|
| GET | `/health` | Public |
| POST | `/admin/documents` | `X-Admin-Key` |
| GET | `/admin/documents` | `X-Admin-Key` |
| DELETE | `/admin/documents/{id}` | `X-Admin-Key` |
| GET | `/admin/ingest-jobs/{id}` | `X-Admin-Key` |
| POST | `/v1/chat/stream` | `X-Student-Key` |

---

## PHỤ LỤC 4. CẤU TRÚC THƯ MỤC MÃ NGUỒN FLUTTER

```
lib/
├── main.dart
├── config/          # api_config, firebase, department_catalog, demo
├── models/
├── providers/       # ChatProvider
├── screens/
├── services/        # RAG, auth, Firestore repos, TTS/STT
├── widgets/
└── theme/
```

---

## PHỤ LỤC 5. ROUTE STAFF CONSOLE

| Route | Trang |
|-------|-------|
| `/login` | Đăng nhập |
| `/` | Tổng quan |
| `/students` | Hồ sơ sinh viên |
| `/chat` | Chat phòng ban |
| `/notifications` | Thông báo |
| `/submissions` | Đơn từ |
| `/feedback` | Góp ý |
| `/vectors` | Tài liệu RAG |
| `/audit` | Nhật ký |
| `/settings` | Cài đặt |

---

## PHỤ LỤC 6. HƯỚNG DẪN GHÉP VÀO WORD

1. Mở mẫu khóa luận của Trường Đại học Thăng Long.
2. Copy từng file `.md` theo thứ tự trong `README.md`.
3. Áp dụng style: Times New Roman 13pt, giãn dòng 1,3 (hoặc 1,5 theo GVHD).
4. Chèn hình: sơ đồ kiến trúc (export từ Mermaid), screenshot app và Staff Console.
5. Tạo Mục lục, Danh mục bảng/hình tự động trong Word.
6. Đánh số trang Ả Rập từ trang Mở đầu.
7. Rà soát trích dẫn `[n]` khớp *Tài liệu tham khảo*.

*Mã nguồn đầy đủ nằm tại thư mục gốc dự án `Graduation_Thesis/` — có thể nộp kèm đĩa/USB theo yêu cầu khoa: `MãSV_Hovaten_MãHọcPhần_Năm.zip`.*
