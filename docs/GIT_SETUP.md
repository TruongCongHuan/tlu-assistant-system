# Git setup & workflow

Hướng dẫn clone, cấu hình secret và quy trình làm việc với monorepo TLU Assistant System.

## Cấu trúc monorepo

| Thư mục | Stack | Vai trò |
|---------|-------|---------|
| `lib/` | Flutter / Dart | Ứng dụng sinh viên (RAG local + Firebase) |
| `services/rag-api/` | Python / FastAPI | RAG server, ChromaDB, eval harness |
| `apps/staff-console/` | React + Node.js | Web cán bộ + BFF Express |
| `docker-compose.yml` | Docker | Orchestrate `rag-api` + `staff-console` |
| `scripts/` | Python / shell | Build KLTN v2, deploy |
| `thesis/content_v2/` | Python | Nội dung khóa luận (nguồn cho `build_thesis_v2.py`) |

**Một repo, nhiều stack** — không cần tách Flutter và Docker sang repo riêng.

## Clone lần đầu

```bash
git clone https://github.com/<username>/tlu-assistant-system.git
cd tlu-assistant-system
```

### Secrets (không có trong Git)

```bash
cp .env.example .env
# Sửa .env: GEMINI_API_KEY, STAFF_JWT_SECRET, ...

mkdir -p secrets
cp /path/to/your-firebase-sa.json secrets/firebase-sa.json
```

Tuỳ chọn Flutter Firebase (nếu build app với Firebase thật):

- `android/app/google-services.json`
- `ios/Runner/GoogleService-Info.plist`

Các file này nằm trong `.gitignore`.

### Chạy backend

```bash
docker compose up --build
```

### Chạy Flutter

```bash
flutter pub get
flutter run \
  --dart-define=GEMINI_KEY=YOUR_KEY \
  --dart-define=API_BASE_URL=http://10.0.2.2:8080 \
  --dart-define=STUDENT_API_KEY=dev-student-key
```

Emulator Android: `10.0.2.2` = localhost máy host.

## File không commit

| Path | Lý do |
|------|-------|
| `.env` | API keys |
| `secrets/` | Firebase service account |
| `build/`, `.dart_tool/` | Flutter build artifacts |
| `apps/staff-console/node_modules/` | npm dependencies |
| `data/` | Runtime JSON / Chroma volume |
| `document/*.docx` | KLTN Word (giữ local hoặc Drive) |

Tái tạo KLTN Word:

```bash
python scripts/build_thesis_v2.py
# → document/KLTN_TruongCongHuan_Final_v2.docx (local only)
```

## Workflow hàng ngày

```bash
git status
git add services/rag-api/app/rag.py
git commit -m "feat(rag): improve semantic chunking overlap"
git push
```

### Nhánh feature (khuyến nghị)

```bash
git checkout -b feat/eval-ablation
# ... chỉnh sửa ...
git push -u origin feat/eval-ablation
# Tạo Pull Request trên GitHub → merge vào main
```

## Chia sẻ với nhà tuyển dụng

- **Public repo:** gửi link GitHub trên CV (đã lọc secret qua `.gitignore`).
- **Private repo:** vào Settings → Collaborators → thêm email recruiter (họ cần tài khoản GitHub).

GitHub private **không** hỗ trợ “ai có link đều xem” như Google Drive.

## Push lên GitHub (lần đầu)

1. Tạo repo trên https://github.com/new (không tick README).
2. Chạy:

```bash
chmod +x scripts/push_to_github.sh
./scripts/push_to_github.sh <github-username> tlu-assistant-system public
```

Hoặc thủ công:

```bash
git remote add origin https://github.com/<username>/tlu-assistant-system.git
git branch -M main
git push -u origin main
```

## Eval RAG (tuỳ chọn)

```bash
cp .env.example .env   # GEMINI_API_KEY
python services/rag-api/eval/ingest_k38.py
python services/rag-api/eval/run_eval.py --ablation
```

Kết quả ghi vào `services/rag-api/eval/results/` (CSV/JSON bị ignore; commit `ablation_placeholder.md` hoặc copy số liệu vào thesis).
