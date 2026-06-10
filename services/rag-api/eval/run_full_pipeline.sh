#!/usr/bin/env bash
# Full eval pipeline:
#   Step 1 — Ablation 12 configs (semantic/fixed × expand × top_k), dense retrieval
#   Step 2 — Dense vs Hybrid (BM25+RRF) comparison, production config (semantic,exp1,k8)
#   Step 3 — Error analysis trên kết quả dense tốt nhất
#   Step 4 — So sánh thống kê dense vs hybrid (McNemar + bootstrap CI) → stats JSON
#
# Monitor: tail -f services/rag-api/eval/logs/pipeline.log
# Usage  : ./services/rag-api/eval/run_full_pipeline.sh

set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
cd "$ROOT"
PY="${ROOT}/.venv/bin/python"
LOG="${ROOT}/services/rag-api/eval/logs/pipeline.log"
mkdir -p "$(dirname "$LOG")"

export PYTHONUNBUFFERED=1
export GEMINI_API_MIN_INTERVAL_SEC="${GEMINI_API_MIN_INTERVAL_SEC:-2}"
export GEMINI_EMBED_MIN_INTERVAL_SEC="${GEMINI_EMBED_MIN_INTERVAL_SEC:-0.8}"
export EMBED_REQUEST_DELAY_MS="${EMBED_REQUEST_DELAY_MS:-0}"
export EMBED_HTTP_BATCH_SIZE="${EMBED_HTTP_BATCH_SIZE:-16}"
export EVAL_SLEEP_SEC="${EVAL_SLEEP_SEC:-0}"
export JUDGE_SINGLE_CALL="${JUDGE_SINGLE_CALL:-1}"
export CURSOR_JUDGE="${CURSOR_JUDGE:-1}"
export CURSOR_GENERATE="${CURSOR_GENERATE:-0}"
export CURSOR_MODEL="${CURSOR_MODEL:-auto}"

echo "=== PIPELINE START $(date) ===" | tee -a "$LOG"

# ── Step 1: Ablation 12 cấu hình (dense) ─────────────────────────────────────
echo "=== STEP 1/4: ABLATION 12 configs (50 q, RETRIEVAL_MODE=dense) ===" | tee -a "$LOG"
RETRIEVAL_MODE=dense \
  "$PY" services/rag-api/eval/run_eval.py --ablation 2>&1 | tee -a "$LOG"

# ── Step 2: Dense vs Hybrid — cùng production config semantic,exp1,k8 ─────────
echo "=== STEP 2/4: DENSE vs HYBRID — semantic,expand=1,k=8 ===" | tee -a "$LOG"

DENSE_ID="cmsemantic_exp1_k8_rmde"
HYBRID_ID="cmsemantic_exp1_k8_rmhy"

# Dense (checkpoint có thể đã có từ step 1)
RETRIEVAL_MODE=dense CHUNK_MODE=semantic EXPAND_ON=1 TOP_K=8 \
  "$PY" services/rag-api/eval/run_eval.py --resume 2>&1 | tee -a "$LOG"

# Hybrid
RETRIEVAL_MODE=hybrid CHUNK_MODE=semantic EXPAND_ON=1 TOP_K=8 \
  "$PY" services/rag-api/eval/run_eval.py --resume 2>&1 | tee -a "$LOG"

# ── Step 3: Error analysis trên dense (production config) ─────────────────────
echo "=== STEP 3/4: ERROR ANALYSIS ===" | tee -a "$LOG"
DENSE_CSV="$("$PY" -c "
from pathlib import Path
results = Path('services/rag-api/eval/results')
candidates = sorted(results.glob('cmsemantic_exp1_k8_rmde*_detail.csv'), key=lambda x: x.stat().st_mtime)
print(candidates[-1] if candidates else '')
" 2>/dev/null || true)"

if [[ -n "$DENSE_CSV" ]]; then
  "$PY" services/rag-api/eval/error_analysis.py "$DENSE_CSV" 2>&1 | tee -a "$LOG"
else
  echo "[WARN] Không tìm thấy dense detail CSV cho error analysis" | tee -a "$LOG"
fi

# ── Step 4: So sánh thống kê Dense vs Hybrid ─────────────────────────────────
echo "=== STEP 4/4: STATISTICAL COMPARISON — Dense vs Hybrid ===" | tee -a "$LOG"
"$PY" - <<'PYEOF' 2>&1 | tee -a "$LOG"
import sys, json
from pathlib import Path

sys.path.insert(0, "services/rag-api")
from eval import stats as eval_stats

results = Path("services/rag-api/eval/results")

def load_latest_checkpoint(prefix: str):
    from eval.run_eval import load_checkpoint_rows
    import os; os.chdir(Path("services/rag-api/eval").parent.parent.parent)
    rows = load_checkpoint_rows(prefix)
    if not rows:
        # fallback to CSV
        candidates = sorted(results.glob(f"{prefix}*_detail.csv"), key=lambda x: x.stat().st_mtime)
        if candidates:
            import csv
            with candidates[-1].open(encoding="utf-8") as f:
                rows = list(csv.DictReader(f))
    return rows

dense_rows  = load_latest_checkpoint("cmsemantic_exp1_k8_rmde")
hybrid_rows = load_latest_checkpoint("cmsemantic_exp1_k8_rmhy")

if not dense_rows or not hybrid_rows:
    print(f"[SKIP] Dense rows={len(dense_rows)}, Hybrid rows={len(hybrid_rows)} — bỏ qua so sánh")
    sys.exit(0)

comparison = eval_stats.compare_runs(
    dense_rows, hybrid_rows,
    label_a="dense", label_b="hybrid"
)
out = results / "dense_vs_hybrid_stats.json"
out.write_text(json.dumps(comparison, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"[SAVED] {out}")
print(json.dumps(comparison, ensure_ascii=False, indent=2))
PYEOF

echo "=== PIPELINE DONE $(date) ===" | tee -a "$LOG"
