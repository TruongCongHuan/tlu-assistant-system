"""RAG Evaluation Harness for TLU AI Assistant.

Metrics (per Chip Huyen, AI Engineering, 2024):
  Retrieval  : context_precision, context_recall, hit_rate_at_k, MRR, NDCG
  Generation : faithfulness (AI-judge), answer_relevance (AI-judge), refusal_accuracy
  Ops        : TTFT, total_latency, output_tokens, embed_cost_usd

Ablation matrix (set via env before each run):
  CHUNK_MODE  = semantic | fixed
  EXPAND_ON   = 1 | 0
  TOP_K       = 5 | 8 | 12

Usage (run from repo root):
    # Ingestion (once per chunk config change):
    CHUNK_MODE=semantic python services/rag-api/eval/ingest_k38.py
    CHUNK_MODE=fixed    python services/rag-api/eval/ingest_k38.py

    # Single run:
    CHUNK_MODE=semantic EXPAND_ON=1 TOP_K=8 python services/rag-api/eval/run_eval.py

    # Full ablation (all 12 configs):
    python services/rag-api/eval/run_eval.py --ablation

Results are written to services/rag-api/eval/results/
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# ── Path setup ────────────────────────────────────────────────────────────────
_here      = Path(__file__).resolve().parent
_repo_root = _here.parent.parent.parent
sys.path.insert(0, str(_here.parent))   # services/rag-api/ -> import app

from dotenv import load_dotenv
load_dotenv(_repo_root / ".env", override=False)

import google.generativeai as genai  # noqa: E402
import app.rag as rag                # noqa: E402

EVAL_SET_PATH = _here / "eval_set.jsonl"
RESULTS_DIR   = _here / "results"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

# ── Load eval set ─────────────────────────────────────────────────────────────

def load_eval_set() -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    with EVAL_SET_PATH.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                items.append(json.loads(line))
    return items


# ── Retrieval metrics ─────────────────────────────────────────────────────────

def is_relevant_chunk(chunk_text: str, relevant_heading: str) -> bool:
    """Heuristic: chunk is relevant if it contains the heading keyword or ground-truth heading."""
    if relevant_heading == "N/A":
        return False
    # Normalize: drop markdown markers, compare case-insensitive keywords
    heading_clean = relevant_heading.replace("##", "").replace("**", "").strip().lower()
    # Extract up to 6 words from heading as keywords
    keywords = [w for w in heading_clean.split() if len(w) > 3][:6]
    chunk_lower = chunk_text.lower()
    return any(kw in chunk_lower for kw in keywords) if keywords else False


def compute_retrieval_metrics(
    retrieved_chunks: list[dict[str, Any]],
    relevant_heading: str,
    k: int,
) -> dict[str, float]:
    """
    context_precision : among retrieved top-k, fraction that are relevant.
    hit_rate_at_k     : 1 if any top-k chunk is relevant, else 0.
    MRR               : 1/rank of first relevant chunk; 0 if none.
    NDCG              : normalized discounted cumulative gain at k.
    """
    if relevant_heading == "N/A":
        # Out-of-scope: no relevant chunks exist → retrieval naturally returns non-relevant
        # We still measure whether the system retrieved anything (it shouldn't for refusal)
        return {
            "context_precision": 0.0,
            "hit_rate_at_k": 0.0,
            "mrr": 0.0,
            "ndcg": 0.0,
        }

    relevances: list[int] = [
        1 if is_relevant_chunk(c["text"], relevant_heading) else 0
        for c in retrieved_chunks[:k]
    ]
    n = len(relevances)
    if n == 0:
        return {"context_precision": 0.0, "hit_rate_at_k": 0.0, "mrr": 0.0, "ndcg": 0.0}

    # Context Precision = TP / (TP + FP)
    context_precision = sum(relevances) / n

    # Hit Rate@k
    hit_rate = 1.0 if any(relevances) else 0.0

    # MRR
    mrr = 0.0
    for rank, rel in enumerate(relevances, start=1):
        if rel == 1:
            mrr = 1.0 / rank
            break

    # NDCG@k (binary relevance)
    dcg  = sum(rel / math.log2(rank + 1) for rank, rel in enumerate(relevances, start=1))
    ideal = [1] + [0] * (n - 1)  # best case: first chunk is relevant
    idcg = sum(r / math.log2(rank + 1) for rank, r in enumerate(ideal, start=1))
    ndcg = dcg / idcg if idcg > 0 else 0.0

    return {
        "context_precision": round(context_precision, 4),
        "hit_rate_at_k": hit_rate,
        "mrr": round(mrr, 4),
        "ndcg": round(ndcg, 4),
    }


# ── AI judge (faithfulness & answer relevance) ────────────────────────────────
# Uses Gemini as judge. Per Chip Huyen (AI Engineering, Table 3-4), scoring system
# is explicitly defined here so results are interpretable and reproducible.
# Scale: 0.0–1.0 for both metrics.

def ai_judge(
    question: str,
    context: str,
    answer: str,
    ground_truth: str,
) -> dict[str, float]:
    """
    faithfulness    : How much of the answer is supported by the retrieved context?
                      (0=none, 1=fully grounded)
    answer_relevance: How relevant and complete is the answer relative to the question
                      and ground truth? (0=irrelevant, 1=fully relevant)

    Note: AI judges are not standardized across tools (Chip Huyen 2024, p.164).
    This harness uses Gemini-flash with explicit 0–1 scoring instructions.
    """
    try:
        rag.configure_genai()
        judge_model = genai.GenerativeModel(rag.LLM_MODEL)

        faithfulness_prompt = f"""You are an evaluator assessing RAG system faithfulness.
CONTEXT (retrieved documents):
{context[:3000]}

ANSWER (generated by the system):
{answer[:1500]}

TASK: Score FAITHFULNESS on a scale 0.0 to 1.0.
- 1.0: Every claim in the answer can be verified from the context.
- 0.5: About half the claims are supported by context.
- 0.0: None of the claims can be inferred from the context (hallucination).

Respond with ONLY a decimal number between 0.0 and 1.0. Example: 0.8"""

        relevance_prompt = f"""You are an evaluator assessing RAG system answer quality.
QUESTION: {question}
GROUND TRUTH ANSWER: {ground_truth[:1000]}
SYSTEM ANSWER: {answer[:1500]}

TASK: Score ANSWER RELEVANCE on a scale 0.0 to 1.0.
- 1.0: The answer fully addresses the question and matches the ground truth.
- 0.5: The answer partially addresses the question.
- 0.0: The answer is irrelevant or completely wrong.

Respond with ONLY a decimal number between 0.0 and 1.0. Example: 0.7"""

        def _score(prompt: str) -> float:
            resp = judge_model.generate_content(prompt)
            text = (resp.text or "0").strip().replace(",", ".")
            # Extract first float-like token
            import re
            m = re.search(r"\b([01](?:\.\d+)?)\b", text)
            return float(m.group(1)) if m else 0.0

        faithfulness     = _score(faithfulness_prompt)
        answer_relevance = _score(relevance_prompt)

        return {
            "faithfulness":      round(min(max(faithfulness, 0.0), 1.0), 3),
            "answer_relevance":  round(min(max(answer_relevance, 0.0), 1.0), 3),
        }
    except Exception as e:  # noqa: BLE001
        print(f"    [WARN] AI judge failed: {e}")
        return {"faithfulness": -1.0, "answer_relevance": -1.0}  # -1 = error marker


# ── Refusal accuracy ──────────────────────────────────────────────────────────

def check_refusal(answer: str) -> bool:
    """True if the system explicitly declined to answer (for out-of-scope queries)."""
    refuse_phrases = [
        "không tìm thấy", "ngoài phạm vi", "không có thông tin",
        "không liên quan", "xin lỗi", "không thuộc", "vui lòng liên hệ",
        "không thể trả lời", "không có trong tài liệu",
    ]
    answer_lower = answer.lower()
    return any(p in answer_lower for p in refuse_phrases)


# ── Single query evaluation ───────────────────────────────────────────────────

def evaluate_one(item: dict[str, Any], top_k: int) -> dict[str, Any]:
    question        = item["question"]
    ground_truth    = item["ground_truth"]
    relevant_heading = item["relevant_heading"]
    category        = item["category"]
    is_oos          = category == "out_of_scope"

    # ── Retrieval (direct call, bypasses stream) ──────────────────────────────
    t_retrieve_start = time.perf_counter()
    context, sources, raw_chunks = rag.retrieve_context(question, doc_id=None, top_k=top_k)
    t_retrieve_end = time.perf_counter()
    retrieval_latency_ms = (t_retrieve_end - t_retrieve_start) * 1000

    # ── Generation (full streaming, collect TTFT + total) ────────────────────
    full_answer = ""
    ttft_ms     = None
    t_gen_start = time.perf_counter()
    try:
        rag.configure_genai()
        for piece in rag.stream_answer(question, doc_id=None):
            if ttft_ms is None:
                ttft_ms = (time.perf_counter() - t_gen_start) * 1000
            full_answer += piece
    except Exception as e:  # noqa: BLE001
        full_answer = f"[ERROR] {e}"
    t_gen_end = time.perf_counter()
    total_latency_ms = (t_gen_end - t_gen_start) * 1000

    output_tokens  = len(full_answer.split())  # rough proxy (word count)
    # Gemini embedding cost estimate: $0.0000004 per character (approximate free-tier equiv)
    embed_cost_usd = len(question) * 0.0000004

    # ── Retrieval metrics ─────────────────────────────────────────────────────
    ret_metrics = compute_retrieval_metrics(raw_chunks, relevant_heading, top_k)

    # ── Refusal accuracy ──────────────────────────────────────────────────────
    refused = check_refusal(full_answer)
    refusal_correct = refused if is_oos else (not refused)

    # ── AI judge ──────────────────────────────────────────────────────────────
    judge_metrics = ai_judge(question, context, full_answer, ground_truth)

    return {
        "id":                   item["id"],
        "category":             category,
        "question":             question,
        "answer":               full_answer[:500],  # truncated for CSV
        "context_precision":    ret_metrics["context_precision"],
        "hit_rate_at_k":        ret_metrics["hit_rate_at_k"],
        "mrr":                  ret_metrics["mrr"],
        "ndcg":                 ret_metrics["ndcg"],
        "faithfulness":         judge_metrics["faithfulness"],
        "answer_relevance":     judge_metrics["answer_relevance"],
        "refusal_correct":      int(refusal_correct),
        "ttft_ms":              round(ttft_ms or 0, 1),
        "total_latency_ms":     round(total_latency_ms, 1),
        "retrieval_latency_ms": round(retrieval_latency_ms, 1),
        "output_tokens_approx": output_tokens,
        "embed_cost_usd":       round(embed_cost_usd, 8),
        "chunk_mode":           rag.CHUNK_MODE,
        "expand_on":            int(rag.EXPAND_ON),
        "top_k":                top_k,
    }


# ── Aggregate stats ───────────────────────────────────────────────────────────

def aggregate(rows: list[dict[str, Any]]) -> dict[str, Any]:
    def avg(key: str) -> float:
        vals = [r[key] for r in rows if isinstance(r[key], (int, float)) and r[key] >= 0]
        return round(sum(vals) / len(vals), 4) if vals else 0.0

    oos_rows  = [r for r in rows if r["category"] == "out_of_scope"]
    non_oos   = [r for r in rows if r["category"] != "out_of_scope"]

    return {
        "n_total":                len(rows),
        "n_oos":                  len(oos_rows),
        "avg_context_precision":  avg("context_precision"),
        "avg_hit_rate_at_k":      avg("hit_rate_at_k"),
        "avg_mrr":                avg("mrr"),
        "avg_ndcg":               avg("ndcg"),
        "avg_faithfulness":       avg("faithfulness"),
        "avg_answer_relevance":   avg("answer_relevance"),
        "refusal_accuracy":       avg("refusal_correct"),
        "avg_ttft_ms":            avg("ttft_ms"),
        "avg_total_latency_ms":   avg("total_latency_ms"),
        "avg_output_tokens":      avg("output_tokens_approx"),
        "total_embed_cost_usd":   round(sum(r["embed_cost_usd"] for r in rows), 6),
        "chunk_mode":             rows[0]["chunk_mode"] if rows else "",
        "expand_on":              rows[0]["expand_on"] if rows else 0,
        "top_k":                  rows[0]["top_k"] if rows else 0,
    }


# ── Save results ──────────────────────────────────────────────────────────────

def save_results(rows: list[dict[str, Any]], run_id: str) -> None:
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    stem = f"{run_id}_{ts}"

    # Per-question CSV
    csv_path = RESULTS_DIR / f"{stem}_detail.csv"
    if rows:
        with csv_path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)
        print(f"[SAVED] {csv_path}")

    # Summary JSON
    summary = aggregate(rows)
    summary["run_id"] = run_id
    summary["timestamp"] = ts
    json_path = RESULTS_DIR / f"{stem}_summary.json"
    json_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[SAVED] {json_path}")

    # Print table
    print("\n── Summary ─────────────────────────────────────────────────────────")
    for k, v in summary.items():
        print(f"  {k:<30} {v}")


def save_ablation_table(summaries: list[dict[str, Any]]) -> None:
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    path = RESULTS_DIR / f"ablation_{ts}.csv"
    if summaries:
        with path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(summaries[0].keys()))
            writer.writeheader()
            writer.writerows(summaries)
    print(f"\n[SAVED] Ablation table → {path}")

    # Also save markdown version for easy copy-paste into thesis
    md_path = RESULTS_DIR / f"ablation_{ts}.md"
    cols = [
        "chunk_mode", "expand_on", "top_k",
        "avg_context_precision", "avg_hit_rate_at_k", "avg_mrr", "avg_ndcg",
        "avg_faithfulness", "avg_answer_relevance", "refusal_accuracy",
        "avg_ttft_ms", "avg_total_latency_ms",
    ]
    header = "| " + " | ".join(cols) + " |"
    sep    = "| " + " | ".join(["---"] * len(cols)) + " |"
    lines  = [header, sep]
    for s in summaries:
        row = "| " + " | ".join(str(s.get(c, "")) for c in cols) + " |"
        lines.append(row)
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"[SAVED] Ablation Markdown → {md_path}")


# ── Main ──────────────────────────────────────────────────────────────────────

def run_single(top_k: int | None = None) -> list[dict[str, Any]]:
    items = load_eval_set()
    k = top_k or rag.TOP_K
    run_id = f"cm{rag.CHUNK_MODE}_exp{int(rag.EXPAND_ON)}_k{k}"
    print(f"\n=== Eval run: {run_id} | {len(items)} questions ===")
    rows: list[dict[str, Any]] = []
    for i, item in enumerate(items, 1):
        print(f"  [{i:02d}/{len(items)}] {item['id']} ({item['category']}) ...", flush=True)
        row = evaluate_one(item, k)
        rows.append(row)
        # Brief pause between questions to respect rate limits
        time.sleep(0.5)
    save_results(rows, run_id)
    return rows


def run_ablation() -> None:
    """Run all 12 ablation configurations and compile summary table."""
    configs = [
        {"CHUNK_MODE": "semantic", "EXPAND_ON": "1", "TOP_K": "5"},
        {"CHUNK_MODE": "semantic", "EXPAND_ON": "1", "TOP_K": "8"},
        {"CHUNK_MODE": "semantic", "EXPAND_ON": "1", "TOP_K": "12"},
        {"CHUNK_MODE": "semantic", "EXPAND_ON": "0", "TOP_K": "5"},
        {"CHUNK_MODE": "semantic", "EXPAND_ON": "0", "TOP_K": "8"},
        {"CHUNK_MODE": "semantic", "EXPAND_ON": "0", "TOP_K": "12"},
        {"CHUNK_MODE": "fixed",    "EXPAND_ON": "1", "TOP_K": "5"},
        {"CHUNK_MODE": "fixed",    "EXPAND_ON": "1", "TOP_K": "8"},
        {"CHUNK_MODE": "fixed",    "EXPAND_ON": "1", "TOP_K": "12"},
        {"CHUNK_MODE": "fixed",    "EXPAND_ON": "0", "TOP_K": "5"},
        {"CHUNK_MODE": "fixed",    "EXPAND_ON": "0", "TOP_K": "8"},
        {"CHUNK_MODE": "fixed",    "EXPAND_ON": "0", "TOP_K": "12"},
    ]
    summaries: list[dict[str, Any]] = []
    for cfg in configs:
        # Patch env vars and reload rag module constants
        os.environ["CHUNK_MODE"] = cfg["CHUNK_MODE"]
        os.environ["EXPAND_ON"]  = cfg["EXPAND_ON"]
        os.environ["TOP_K"]      = cfg["TOP_K"]
        # Reload constants from env
        rag.CHUNK_MODE  = cfg["CHUNK_MODE"]
        rag.EXPAND_ON   = cfg["EXPAND_ON"] not in ("0", "false", "no")
        rag.TOP_K       = int(cfg["TOP_K"])

        print(f"\n{'='*60}")
        print(f"CONFIG: CHUNK_MODE={cfg['CHUNK_MODE']} EXPAND_ON={cfg['EXPAND_ON']} TOP_K={cfg['TOP_K']}")
        print(f"  Note: Re-ingest required for CHUNK_MODE change (run ingest_k38.py first).")
        print(f"{'='*60}")

        rows = run_single(top_k=int(cfg["TOP_K"]))
        summaries.append(aggregate(rows))

    save_ablation_table(summaries)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="TLU RAG Evaluation Harness")
    parser.add_argument("--ablation", action="store_true",
                        help="Run full 12-config ablation matrix")
    parser.add_argument("--top-k", type=int, default=None,
                        help="Override TOP_K for single run")
    args = parser.parse_args()

    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        print("[ERROR] GEMINI_API_KEY not set. Add to .env or export.")
        sys.exit(1)

    if args.ablation:
        run_ablation()
    else:
        run_single(top_k=args.top_k)
