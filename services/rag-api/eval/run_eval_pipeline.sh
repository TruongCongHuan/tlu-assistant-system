#!/usr/bin/env bash
# Eval pipeline: ingest (if needed) + 50-question run with checkpoint/resume.
#
# LLM backends:
#   - Retrieval/embedding: Gemini (luôn dùng GEMINI_API_KEY)
#   - Judge + Generation : Cursor model khi CURSOR_API_KEY có trong .env
#                          (ngược lại fallback về Gemini)
#
# Usage (from repo root):
#   1. Đặt GEMINI_API_KEY (embed) + CURSOR_API_KEY (judge/gen) trong .env
#   2. ./services/rag-api/eval/run_eval_pipeline.sh
#   3. On quota pause: swap key in .env, re-run same script (auto-resumes)
#   4. Chỉ dùng Cursor cho generation: CURSOR_GENERATE=1 ./... run_eval_pipeline.sh

set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
cd "$ROOT"
PY="${PYTHON_BIN:-${ROOT}/services/rag-api/.venv/bin/python}"
export CHUNK_MODE="${CHUNK_MODE:-semantic}"
export EXPAND_ON="${EXPAND_ON:-1}"
export TOP_K="${TOP_K:-8}"
export GEMINI_API_MIN_INTERVAL_SEC="${GEMINI_API_MIN_INTERVAL_SEC:-7.5}"
export EMBED_REQUEST_DELAY_MS="${EMBED_REQUEST_DELAY_MS:-800}"
# Cursor backend (đọc từ .env nếu không truyền qua env)
export CURSOR_JUDGE="${CURSOR_JUDGE:-1}"
export CURSOR_GENERATE="${CURSOR_GENERATE:-0}"
export CURSOR_MODEL="${CURSOR_MODEL:-auto}"

if [[ ! -f .env ]] || ! grep -q '^GEMINI_API_KEY=.\+' .env 2>/dev/null; then
  echo "[ERROR] Thiếu GEMINI_API_KEY trong ${ROOT}/.env"
  echo "  GEMINI_API_KEY=your_key  # https://aistudio.google.com/apikey"
  exit 1
fi

# Thông báo Cursor backend
if grep -q '^CURSOR_API_KEY=.\+' .env 2>/dev/null || [[ -n "${CURSOR_API_KEY:-}" ]]; then
  echo "[INFO] CURSOR_API_KEY tìm thấy — judge=${CURSOR_JUDGE} generate=${CURSOR_GENERATE} model=${CURSOR_MODEL}"
else
  echo "[INFO] CURSOR_API_KEY chưa đặt — dùng Gemini cho judge và generation"
fi

CHROMA="${CHROMA_DATA_DIR:-${ROOT}/services/rag-api/eval/.chroma_eval}"
export CHROMA_DATA_DIR="$CHROMA"
export SOURCES_DIR="${SOURCES_DIR:-${ROOT}/services/rag-api/eval/.sources}"
if [[ ! -d "$CHROMA" ]] || [[ -z "$(ls -A "$CHROMA" 2>/dev/null || true)" ]]; then
  echo "[INFO] Chưa có corpus trong Chroma → ingest K38 …"
  "$PY" services/rag-api/eval/ingest_k38.py
else
  echo "[INFO] Chroma đã có dữ liệu tại $CHROMA — bỏ qua ingest"
fi

echo "[INFO] Chạy eval 50 câu (checkpoint/resume) …"
"$PY" services/rag-api/eval/run_eval.py --resume
