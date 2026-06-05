# Triển khai GCP — Cloud Run + Artifact Registry + Secret Manager

Tài liệu này thay cho việc tạo project trên máy bạn; thực hiện từng bước trên [Google Cloud Console](https://console.cloud.google.com/).

## 1. Tạo project & billing alert

1. Console → **Select a project** → **New Project** → đặt tên (ví dụ `tlu-ai-assistant-demo`).
2. **Billing** → liên kết billing account (Cloud Run thường cần thẻ dù có free tier).
3. **Billing** → **Budgets & alerts** → Create budget → ngưỡng 5–10 USD → email cảnh báo.

## 2. Bật API

```bash
gcloud services enable run.googleapis.com artifactregistry.googleapis.com secretmanager.googleapis.com cloudbuild.googleapis.com
```

(Hoặc trong Console: **APIs & Services** → Enable **Cloud Run Admin**, **Artifact Registry**, **Secret Manager**.)

## 3. Cài gcloud & đăng nhập

```bash
gcloud auth login
gcloud config set project YOUR_PROJECT_ID
```

## 4. Artifact Registry (Docker)

```bash
export REGION=asia-southeast1
export REPO=rag-api

gcloud artifacts repositories create $REPO \
  --repository-format=docker \
  --location=$REGION \
  --description="RAG API images"
```

Đăng nhập Docker vào Artifact Registry:

```bash
gcloud auth configure-docker ${REGION}-docker.pkg.dev
```

## 5. Secret Manager — Gemini API key

```bash
echo -n "YOUR_GEMINI_API_KEY" | gcloud secrets create gemini-api-key --data-file=-
```

Cấp quyền đọc secret cho service account mà Cloud Run dùng (sau khi deploy lần đầu, hoặc dùng Compute default SA):

```bash
PROJECT_NUMBER=$(gcloud projects describe $(gcloud config get-value project) --format='value(projectNumber)')
gcloud secrets add-iam-policy-binding gemini-api-key \
  --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

## 6. Build & push image

Từ thư mục gốc repo (hoặc chạy [scripts/deploy_cloud_run.sh](../scripts/deploy_cloud_run.sh) sau khi chỉnh biến môi trường):

```bash
export REGION=asia-southeast1
export PROJECT_ID=$(gcloud config get-value project)
export IMAGE=${REGION}-docker.pkg.dev/${PROJECT_ID}/rag-api/rag-api:latest

docker build -t $IMAGE -f services/rag-api/Dockerfile services/rag-api
docker push $IMAGE
```

## 7. Deploy Cloud Run

```bash
gcloud run deploy rag-api \
  --image $IMAGE \
  --region $REGION \
  --platform managed \
  --allow-unauthenticated \
  --memory 2Gi \
  --timeout 300 \
  --set-secrets GEMINI_API_KEY=gemini-api-key:latest \
  --set-env-vars "ADMIN_API_KEY=your-admin-secret,STUDENT_API_KEY=your-student-secret,CHROMA_DATA_DIR=/tmp/chroma,CORS_ORIGINS=*"
```

**Lưu ý bảo mật:** `--allow-unauthenticated` vẫn cho phép gọi URL công khai; API của bạn **bắt buộc** header `X-Admin-Key` / `X-Student-Key`. Để chặn hoàn toàn anonymous, dùng **IAM** trên Cloud Run (bỏ `--allow-unauthenticated`) và chỉ cho phép principal cụ thể — phức tạp hơn cho demo mobile.

**CORS:** đặt `CORS_ORIGINS` = URL dashboard (ví dụ `https://xxx.web.app,https://xxx.run.app`).

## 8. Smoke test

```bash
export URL=$(gcloud run services describe rag-api --region $REGION --format 'value(status.url)')
curl -sS "$URL/health"
curl -sS -H "X-Student-Key: your-student-secret" -H "Content-Type: application/json" \
  -d '{"question":"Xin chào"}' "$URL/v1/chat/stream"
```

## 9. Vector persistence trên Cloud Run (trade-off)

- **Filesystem `/tmp`:** mất khi instance thu hồi; chỉ ổn cho demo ngắn.
- **GCS backup / restore:** xem [VECTOR_PERSISTENCE.md](VECTOR_PERSISTENCE.md) — đồng bộ thư mục Chroma lên bucket (MVP có thể làm tay hoặc cron).
- **pgvector (Cloud SQL):** bền nhất, công sức DevOps cao hơn.

## 10. Web cán bộ (một cổng)

Build & chạy qua **`docker compose`** (image `staff-console`, cổng 3000) hoặc deploy image đó lên Cloud Run / VM. Cấu hình `STAFF_API_KEY`, `RAG_API_URL`, `RAG_ADMIN_KEY` (trùng `ADMIN_API_KEY` của rag-api), và credential Firebase (`FIREBASE_SERVICE_ACCOUNT_JSON` hoặc `GOOGLE_APPLICATION_CREDENTIALS`). Không cần build Vite riêng nếu dùng Dockerfile trong `apps/staff-console/`.
