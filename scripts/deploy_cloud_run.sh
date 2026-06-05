#!/usr/bin/env bash
# Build, push, deploy rag-api to Cloud Run. Set REGION, PROJECT_ID or rely on gcloud default.
set -euo pipefail

REGION="${REGION:-asia-southeast1}"
REPO="${REPO:-rag-api}"
SERVICE="${SERVICE:-rag-api}"
IMAGE_NAME="${IMAGE_NAME:-rag-api}"

PROJECT_ID="${PROJECT_ID:-$(gcloud config get-value project 2>/dev/null)}"
if [[ -z "${PROJECT_ID}" || "${PROJECT_ID}" == "(unset)" ]]; then
  echo "Set PROJECT_ID or run: gcloud config set project YOUR_PROJECT"
  exit 1
fi

IMAGE="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO}/${IMAGE_NAME}:latest"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "Building ${IMAGE} ..."
docker build -t "${IMAGE}" -f "${ROOT}/services/rag-api/Dockerfile" "${ROOT}/services/rag-api"

echo "Pushing ..."
docker push "${IMAGE}"

echo "Deploying Cloud Run service ${SERVICE} ..."
# Adjust secrets/env to match your Secret Manager resource IDs.
gcloud run deploy "${SERVICE}" \
  --image "${IMAGE}" \
  --region "${REGION}" \
  --platform managed \
  --allow-unauthenticated \
  --memory 2Gi \
  --timeout 300 \
  --set-secrets "GEMINI_API_KEY=gemini-api-key:latest" \
  --set-env-vars "ADMIN_API_KEY=${ADMIN_API_KEY:-change-me-admin},STUDENT_API_KEY=${STUDENT_API_KEY:-change-me-student},CHROMA_DATA_DIR=/tmp/chroma,CORS_ORIGINS=${CORS_ORIGINS:-*}"

echo "Done. URL:"
gcloud run services describe "${SERVICE}" --region "${REGION}" --format 'value(status.url)'
