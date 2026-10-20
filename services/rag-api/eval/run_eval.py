"""RAG Evaluation Harness for TLU AI Assistant.

Metrics (per Chip Huyen, AI Engineering, 2024):
  Retrieval  : context_precision, context_recall, hit_rate_at_k, MRR, NDCG
  Generation : faithfulness (AI-judge), answer_relevance (AI-judge), refusal_accuracy
  Ops        : TTFT, total_latency, output_tokens, embed_cost_usd

Ablation matrix (set via env before each run):
  CHUNK_MODE  = semantic | fixed
  EXPAND_ON   = 1 | 0
  TOP_K       = 5 | 8 | 12

LLM backend (env vars):
  CURSOR_API_KEY    = <key>  → bật Cursor SDK làm judge + (tuỳ chọn) generation
  CURSOR_JUDGE      = 1      → dùng Cursor model làm AI judge (mặc định khi có CURSOR_API_KEY)
  CURSOR_GENERATE   = 0      → dùng Cursor model sinh câu trả lời thay rag.stream_answer()
  CURSOR_MODEL      = auto   → model slug cho Cursor SDK (mặc định: auto)

Usage (run from repo root):
    # Ingestion (once per chunk config change):
    CHUNK_MODE=semantic python services/rag-api/eval/ingest_k38.py
    CHUNK_MODE=fixed    python services/rag-api/eval/ingest_k38.py

    # Single run (Cursor judge, Gemini RAG generation):
    CHUNK_MODE=semantic EXPAND_ON=1 TOP_K=8 python services/rag-api/eval/run_eval.py

    # Single run (Cursor cho cả judge + generation):
    CURSOR_GENERATE=1 python services/rag-api/eval/run_eval.py

    # Full ablation (all 12 configs):
    python services/rag-api/eval/run_eval.py --ablation

Results are written to services/rag-api/eval/results/
"""
from __future__ import annotations

import argparse
import hashlib
from functools import lru_cache
import concurrent.futures
import csv
import json
import math
import os
import re
import sys
import threading
import time
import urllib.error
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# ── Path setup ────────────────────────────────────────────────────────────────
_here      = Path(__file__).resolve().parent
_repo_root = _here.parent.parent.parent
sys.path.insert(0, str(_here.parent))   # services/rag-api/ -> import app

from dotenv import load_dotenv
load_dotenv(_repo_root / ".env", override=True)

os.environ.setdefault("GEMINI_API_MIN_INTERVAL_SEC", "2")
os.environ.setdefault("GEMINI_EMBED_MIN_INTERVAL_SEC", "0.8")
os.environ.setdefault("EMBED_REQUEST_DELAY_MS", "0")
os.environ.setdefault("JUDGE_SINGLE_CALL", "1")

import google.generativeai as genai  # noqa: E402
import app.rag as rag                # noqa: E402
from eval import stats as eval_stats  # noqa: E402

# ── Cursor SDK (optional) ─────────────────────────────────────────────────────
try:
    from cursor_sdk import Agent, AgentOptions, LocalAgentOptions, CursorAgentError
    _CURSOR_SDK_AVAILABLE = True
except ImportError:
    _CURSOR_SDK_AVAILABLE = False

CURSOR_API_KEY    = os.environ.get("CURSOR_API_KEY", "").strip()
CURSOR_MODEL      = os.environ.get("CURSOR_MODEL", "auto").strip()
_cursor_judge_env = os.environ.get("CURSOR_JUDGE", "").strip()
_cursor_gen_env   = os.environ.get("CURSOR_GENERATE", "0").strip()

# Cursor judge là mặc định khi có CURSOR_API_KEY (trừ khi tắt rõ ràng)
USE_CURSOR_JUDGE    = (
    _CURSOR_SDK_AVAILABLE
    and bool(CURSOR_API_KEY)
    and _cursor_judge_env.lower() not in ("0", "false", "no")
)
USE_CURSOR_GENERATE = (
    _CURSOR_SDK_AVAILABLE
    and bool(CURSOR_API_KEY)
    and _cursor_gen_env.lower() not in ("0", "false", "no")
)

_eval_set_override: Path | None = None


def get_eval_set_path() -> Path:
    return _eval_set_override or (_here / "eval_set.jsonl")
RESULTS_DIR   = _here / "results"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

# Canonical column order for _detail.csv — thêm field mới vào đây, không dùng rows[0].keys()
DETAIL_FIELDNAMES = [
    "id", "category", "quality_tag",
    "question", "ground_truth", "answer", "sources", "retrieved_context",
    "context_precision", "hit_rate_at_k", "mrr", "ndcg",
    "faithfulness", "answer_relevance", "refusal_correct",
    "ttft_ms", "total_latency_ms", "retrieval_latency_ms", "pipeline_latency_ms",
    "context_chars", "output_tokens_approx", "embed_cost_usd",
    "chunk_mode", "expand_on", "top_k", "max_context", "max_output_tokens",
    "retrieval_mode",
]

EXIT_QUOTA = 42
EXIT_AUTH = 43

_checkpoint_lock = threading.Lock()


class QuotaExhaustedError(RuntimeError):
    pass


def is_quota_error(exc: BaseException) -> bool:
    msg = str(exc).lower()
    if any(k in msg for k in ("429", "resource exhausted", "resourceexhausted", "quota exceeded")):
        return True
    if isinstance(exc, urllib.error.HTTPError) and exc.code == 429:
        return True
    return False


def is_auth_error(exc: BaseException) -> bool:
    msg = str(exc).lower()
    return any(k in msg for k in ("401", "403", "api_key_invalid", "api key expired"))


def make_run_id(top_k: int) -> str:
    rm = os.environ.get("RETRIEVAL_MODE", "dense").lower()
    rm_suffix = "_rmde" if rm == "dense" else f"_rm{rm[:2]}"
    mc = int(os.environ.get("MAX_CONTEXT", str(rag.MAX_CONTEXT)))
    mot = int(os.environ.get("MAX_OUTPUT_TOKENS", str(rag.MAX_OUTPUT_TOKENS)))
    from eval.build_retrieval_dataset import CORPUS, DATASET
    identity = {"eval": hashlib.sha256(get_eval_set_path().read_bytes()).hexdigest(),
                "corpus": hashlib.sha256(CORPUS.read_bytes()).hexdigest(),
                "qrels": hashlib.sha256((DATASET / "qrels.jsonl").read_bytes()).hexdigest(),
                "embedding": rag.GEMINI_EMBED_REST_MODEL, "llm": rag.LLM_MODEL,
                "collection": rag.COLLECTION_NAME, "bm25_weight": rag.BM25_WEIGHT,
                "rerank": rag.RERANK_MODE, "candidate_k": rag.CANDIDATE_K, "final_k": rag.FINAL_K,
                "rerank_revision": os.getenv("RERANK_REVISION", "default"),
                "source": hashlib.sha256(Path(rag.__file__).read_bytes()).hexdigest()}
    suffix = hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()[:12]
    return (
        f"cm{rag.CHUNK_MODE}_exp{int(rag.EXPAND_ON)}_k{top_k}"
        f"_mc{mc}_mot{mot}{rm_suffix}_{suffix}"
    )


def apply_env_config() -> None:
    """Sync rag module globals from current environment."""
    rag.CHUNK_MODE = os.environ.get("CHUNK_MODE", rag.CHUNK_MODE).lower()
    rag.EXPAND_ON = os.environ.get("EXPAND_ON", "1") not in ("0", "false", "no")
    rag.TOP_K = int(os.environ.get("TOP_K", str(rag.TOP_K)))
    rag.MAX_CONTEXT = int(os.environ.get("MAX_CONTEXT", str(rag.MAX_CONTEXT)))
    rag.MAX_OUTPUT_TOKENS = int(os.environ.get("MAX_OUTPUT_TOKENS", str(rag.MAX_OUTPUT_TOKENS)))
    rag.RETRIEVAL_MODE = os.environ.get("RETRIEVAL_MODE", rag.RETRIEVAL_MODE).lower()


def checkpoint_path(run_id: str) -> Path:
    return RESULTS_DIR / f"checkpoint_{run_id}.jsonl"


def load_checkpoint_rows(run_id: str) -> list[dict[str, Any]]:
    path = checkpoint_path(run_id)
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    by_id: dict[str, dict[str, Any]] = {}
    for row in rows:
        by_id[str(row["id"])] = row
    return [by_id[k] for k in sorted(by_id.keys())]


def config_is_complete(run_id: str) -> bool:
    return len(load_checkpoint_rows(run_id)) >= len(load_eval_set())


def append_checkpoint(run_id: str, row: dict[str, Any]) -> None:
    path = checkpoint_path(run_id)
    with _checkpoint_lock:
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
        size = path.stat().st_size
    print(f"    [CHECKPOINT] {row['id']} → {path.name} ({size} bytes)")


def print_quota_pause(run_id: str, total: int) -> None:
    done = len(load_checkpoint_rows(run_id))
    print("\n" + "=" * 60)
    print(f"[QUOTA_EXHAUSTED] Đã lưu {done}/{total} câu.")
    print(f"  Checkpoint: {checkpoint_path(run_id)}")
    print("  → Sửa GEMINI_API_KEY trong .env (repo root), rồi chạy lại CÙNG lệnh")
    print("=" * 60)

# ── Load eval set ─────────────────────────────────────────────────────────────

def load_eval_set() -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    with get_eval_set_path().open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                items.append(json.loads(line))
    return items


# ── Retrieval metrics ─────────────────────────────────────────────────────────

@lru_cache(maxsize=1)
def _gold_snapshot():
    from eval.build_retrieval_dataset import DATASET, read_jsonl, normalize, validate
    validate()
    chunks = read_jsonl(DATASET / "chunks.jsonl")
    text_ids = {normalize(c["text"]): c["id"] for c in chunks}
    qrels = read_jsonl(DATASET / "qrels.jsonl")
    return text_ids, qrels


def compute_retrieval_metrics(retrieved_chunks, relevant_heading, k, *, query_id=None):
    """Known-gold source judgments; OOS is excluded, never scored by heading words."""
    from eval.retrieval_metrics import retrieval_metrics
    from eval.build_retrieval_dataset import normalize
    if relevant_heading == "N/A":
        return dict.fromkeys(["context_precision", "context_recall", "hit_rate_at_k", "mrr", "ndcg"])
    if query_id is None:
        raise ValueError("query_id is required for source-judged retrieval evaluation")
    text_ids, qrels = _gold_snapshot()
    grades = {r["chunk_id"]: r["relevance"] for r in qrels if r["query_id"] == query_id}
    ids = [text_ids.get(normalize(c["text"]), "unjudged:" + str(c["id"])) for c in retrieved_chunks]
    result = retrieval_metrics(ids, grades, k=k)
    return {"context_precision": result[f"precision@{k}"], "context_recall": result[f"recall@{k}"],
            "hit_rate_at_k": result[f"hit@{k}"], "mrr": result[f"mrr@{k}"], "ndcg": result[f"ndcg@{k}"]}


# ── Judge prompt (shared by both backends) ────────────────────────────────────

_JUDGE_COMBINED_PROMPT = """\
You are an evaluator for a RAG system. Return ONLY valid JSON with two keys.
CONTEXT:
{context}

QUESTION: {question}
GROUND TRUTH: {ground_truth}
SYSTEM ANSWER: {answer}

Score 0.0-1.0:
- faithfulness: claims supported by context
- answer_relevance: answer addresses question vs ground truth

Example: {{"faithfulness": 0.85, "answer_relevance": 0.80}}"""


def _parse_judge_scores(text: str) -> tuple[float, float]:
    m = re.search(r"\{[^{}]*\}", text, re.DOTALL)
    if m:
        try:
            obj = json.loads(m.group(0))
            return float(obj.get("faithfulness", 0)), float(obj.get("answer_relevance", 0))
        except (ValueError, KeyError):
            pass
    return 0.0, 0.0


# ── AI judge — Cursor SDK backend ─────────────────────────────────────────────

def _cursor_ai_judge(
    question: str,
    context: str,
    answer: str,
    ground_truth: str,
) -> dict[str, float]:
    """Judge bằng Cursor model qua cursor_sdk.Agent.prompt()."""
    prompt = _JUDGE_COMBINED_PROMPT.format(
        context=context,
        question=question,
        ground_truth=ground_truth[:1000],
        answer=answer[:1500],
    )
    try:
        result = Agent.prompt(
            prompt,
            AgentOptions(
                api_key=CURSOR_API_KEY,
                model=CURSOR_MODEL,
                local=LocalAgentOptions(cwd=str(_repo_root)),
            ),
        )
        text = (result.result or "").strip()
        if result.status == "error":
            print(f"    [WARN] Cursor judge run failed (id={result.id})")
            return {"faithfulness": -1.0, "answer_relevance": -1.0}
        faithfulness, answer_relevance = _parse_judge_scores(text)
        return {
            "faithfulness":     round(min(max(faithfulness, 0.0), 1.0), 3),
            "answer_relevance": round(min(max(answer_relevance, 0.0), 1.0), 3),
        }
    except CursorAgentError as e:
        print(f"    [WARN] Cursor judge startup error: {e.message} (retryable={e.is_retryable})")
        return {"faithfulness": -1.0, "answer_relevance": -1.0}
    except Exception as e:  # noqa: BLE001
        print(f"    [WARN] Cursor judge error: {e}")
        return {"faithfulness": -1.0, "answer_relevance": -1.0}


# ── AI judge — Gemini backend ─────────────────────────────────────────────────

def _gemini_ai_judge(
    question: str,
    context: str,
    answer: str,
    ground_truth: str,
) -> dict[str, float]:
    """Judge bằng Gemini (fallback khi không có CURSOR_API_KEY)."""
    try:
        rag.configure_genai()
        judge_model = genai.GenerativeModel(rag.LLM_MODEL)
        single_call = os.environ.get("JUDGE_SINGLE_CALL", "1").lower() not in ("0", "false", "no")
        if single_call:
            prompt = _JUDGE_COMBINED_PROMPT.format(
                context=context,
                question=question,
                ground_truth=ground_truth[:1000],
                answer=answer[:1500],
            )
            resp = judge_model.generate_content(prompt)
            text = (resp.text or "").strip()
            faithfulness, answer_relevance = _parse_judge_scores(text)
            return {
                "faithfulness":     round(min(max(faithfulness, 0.0), 1.0), 3),
                "answer_relevance": round(min(max(answer_relevance, 0.0), 1.0), 3),
            }

        def _score(p: str) -> float:
            resp = judge_model.generate_content(p)
            text = (resp.text or "0").strip().replace(",", ".")
            m = re.search(r"\b([01](?:\.\d+)?)\b", text)
            return float(m.group(1)) if m else 0.0

        faithfulness_prompt = f"""You are an evaluator assessing RAG system faithfulness.
CONTEXT (retrieved documents):
{context}

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

        return {
            "faithfulness":     round(min(max(_score(faithfulness_prompt), 0.0), 1.0), 3),
            "answer_relevance": round(min(max(_score(relevance_prompt), 0.0), 1.0), 3),
        }
    except Exception as e:  # noqa: BLE001
        if is_quota_error(e):
            raise QuotaExhaustedError(str(e)) from e
        print(f"    [WARN] Gemini judge failed: {e}")
        return {"faithfulness": -1.0, "answer_relevance": -1.0}


# ── AI judge (faithfulness & answer relevance) ────────────────────────────────
# Per Chip Huyen (AI Engineering, Table 3-4), scoring is explicitly defined so
# results are interpretable and reproducible. Scale: 0.0–1.0.
# Backend: Cursor model khi có CURSOR_API_KEY, ngược lại dùng Gemini.

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
    """
    if USE_CURSOR_JUDGE:
        return _cursor_ai_judge(question, context, answer, ground_truth)
    return _gemini_ai_judge(question, context, answer, ground_truth)


# ── Generation — Cursor backend ───────────────────────────────────────────────

def _cursor_generate(question: str, context: str, sources: str = "") -> str:
    """Sinh câu trả lời qua Cursor SDK dùng ĐÚNG prompt + system instruction của production rag.py."""
    if not context:
        return rag.NO_CONTEXT_REPLY

    # Dùng chính xác prompt + system instruction của rag.stream_answer()
    prompt = f"{rag.SYSTEM_INSTRUCTION}\n\n{rag.build_generation_prompt(question, context, sources)}"
    try:
        result = Agent.prompt(
            prompt,
            AgentOptions(
                api_key=CURSOR_API_KEY,
                model=CURSOR_MODEL,
                local=LocalAgentOptions(cwd=str(_repo_root)),
            ),
        )
        if result.status == "error":
            return f"[CURSOR_ERROR] run_id={result.id}"
        return (result.result or "").strip()
    except CursorAgentError as e:
        return f"[CURSOR_STARTUP_ERROR] {e.message}"
    except Exception as e:  # noqa: BLE001
        return f"[ERROR] {e}"


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


# ── Quality tag (cho BGK xem nhanh) ──────────────────────────────────────────

def quality_tag(
    category: str,
    hit_rate: float,
    faithfulness: float,
    answer_relevance: float,
    refusal_correct: bool,
) -> str:
    """Nhãn đánh giá tổng hợp mỗi câu — dễ lọc khi trình bày cho BGK.

    out_of_scope_ok  : câu ngoài phạm vi, hệ thống từ chối đúng
    out_of_scope_fail: câu ngoài phạm vi nhưng hệ thống trả lời bừa
    good             : retrieve đúng, faithful, relevant
    low_faithfulness : retrieve đúng nhưng câu trả lời bịa/không bám context
    retrieval_miss   : không tìm được đoạn liên quan
    low_relevance    : retrieve ok, faithful ok nhưng câu trả lời lạc đề
    error            : lỗi hệ thống (judge trả -1)
    """
    if category == "out_of_scope":
        return "out_of_scope_ok" if refusal_correct else "out_of_scope_fail"
    if faithfulness < 0 or answer_relevance < 0:
        return "error"
    if hit_rate == 0:
        return "retrieval_miss"
    if faithfulness < 0.5:
        return "low_faithfulness"
    if answer_relevance < 0.5:
        return "low_relevance"
    return "good"


# ── Single query evaluation ───────────────────────────────────────────────────

def evaluate_one(item: dict[str, Any], top_k: int) -> dict[str, Any]:
    question        = item["question"]
    ground_truth    = item["ground_truth"]
    relevant_heading = item["relevant_heading"]
    category        = item["category"]
    is_oos          = category == "out_of_scope"

    # ── Retrieval (direct call, bypasses stream) ──────────────────────────────
    t_retrieve_start = time.perf_counter()
    try:
        context, sources, raw_chunks = rag.retrieve_context(question, doc_id=None, top_k=top_k)
    except Exception as e:  # noqa: BLE001
        if is_quota_error(e):
            raise QuotaExhaustedError(str(e)) from e
        raise
    t_retrieve_end = time.perf_counter()
    retrieval_latency_ms = (t_retrieve_end - t_retrieve_start) * 1000

    # ── Generation (streaming hoặc Cursor one-shot) ───────────────────────────
    full_answer = ""
    ttft_ms     = None
    t_gen_start = time.perf_counter()
    if USE_CURSOR_GENERATE:
        full_answer = _cursor_generate(question, context, sources)
        ttft_ms = (time.perf_counter() - t_gen_start) * 1000
    else:
        try:
            rag.configure_genai()
            for piece in rag.stream_answer(question, doc_id=None, context=context, sources=sources):
                if ttft_ms is None:
                    ttft_ms = (time.perf_counter() - t_gen_start) * 1000
                full_answer += piece
        except Exception as e:  # noqa: BLE001
            if is_quota_error(e):
                raise QuotaExhaustedError(str(e)) from e
            full_answer = f"[ERROR] {e}"
    t_gen_end = time.perf_counter()
    total_latency_ms = (t_gen_end - t_gen_start) * 1000

    output_tokens  = len(full_answer.split())  # rough proxy (word count)
    context_chars  = len(context)
    pipeline_latency_ms = retrieval_latency_ms + total_latency_ms
    # Gemini embedding cost estimate: $0.0000004 per character (approximate free-tier equiv)
    embed_cost_usd = None  # usage accounting is unavailable in this legacy harness

    # ── Retrieval metrics ─────────────────────────────────────────────────────
    ret_metrics = compute_retrieval_metrics(raw_chunks, relevant_heading, top_k, query_id=item["id"])

    # ── Refusal accuracy ──────────────────────────────────────────────────────
    refused = check_refusal(full_answer)
    refusal_correct = refused if is_oos else (not refused)

    # ── AI judge ──────────────────────────────────────────────────────────────
    judge_metrics = ai_judge(question, context, full_answer, ground_truth)

    tag = quality_tag(
        category,
        ret_metrics["hit_rate_at_k"],
        judge_metrics["faithfulness"],
        judge_metrics["answer_relevance"],
        refusal_correct,
    )

    return {
        # ── Nhận diện ──────────────────────────────────────────────────────
        "id":                   item["id"],
        "category":             category,
        "quality_tag":          tag,
        # ── Nội dung câu hỏi / trả lời đầy đủ (cho BGK) ──────────────────
        "question":             question,
        "ground_truth":         ground_truth[:600],
        "answer":               full_answer,          # không cắt
        "sources":              sources,
        "retrieved_context":    context,              # preserve exact generation context
        # ── Chỉ số retrieval ───────────────────────────────────────────────
        "context_precision":    ret_metrics["context_precision"],
        "context_recall":       ret_metrics["context_recall"],
        "ranked_chunks":        raw_chunks,
        "metric_cutoff":        top_k,
        "relevance_protocol":   "source_checked_known_gold_v1",
        "hit_rate_at_k":        ret_metrics["hit_rate_at_k"],
        "mrr":                  ret_metrics["mrr"],
        "ndcg":                 ret_metrics["ndcg"],
        # ── Chỉ số generation ──────────────────────────────────────────────
        "faithfulness":         judge_metrics["faithfulness"],
        "answer_relevance":     judge_metrics["answer_relevance"],
        "refusal_correct":      int(refusal_correct),
        # ── Ops ────────────────────────────────────────────────────────────
        "ttft_ms":              round(ttft_ms or 0, 1),
        "total_latency_ms":     round(total_latency_ms, 1),
        "retrieval_latency_ms": round(retrieval_latency_ms, 1),
        "pipeline_latency_ms":  round(pipeline_latency_ms, 1),
        "context_chars":        context_chars,
        "output_tokens_approx": output_tokens,
        "embed_cost_usd":       embed_cost_usd,
        # ── Config ─────────────────────────────────────────────────────────
        "chunk_mode":           rag.CHUNK_MODE,
        "expand_on":            int(rag.EXPAND_ON),
        "top_k":                top_k,
        "max_context":          rag.MAX_CONTEXT,
        "max_output_tokens":    rag.MAX_OUTPUT_TOKENS,
        "retrieval_mode":       rag.RETRIEVAL_MODE,
    }


# ── Aggregate stats ───────────────────────────────────────────────────────────

def aggregate(rows: list[dict[str, Any]]) -> dict[str, Any]:
    def avg(key: str, pool=None):
        vals = [r[key] for r in (rows if pool is None else pool) if isinstance(r.get(key), (int, float)) and r[key] >= 0]
        return round(sum(vals) / len(vals), 4) if vals else None

    oos_rows  = [r for r in rows if r["category"] == "out_of_scope"]
    non_oos   = [r for r in rows if r["category"] != "out_of_scope"]

    return {
        "n_total":                len(rows),
        "n_oos":                  len(oos_rows),
        "avg_context_precision":  avg("context_precision", non_oos),
        "avg_hit_rate_at_k":      avg("hit_rate_at_k", non_oos),
        "avg_mrr":                avg("mrr", non_oos),
        "avg_ndcg":               avg("ndcg", non_oos),
        "avg_faithfulness":       avg("faithfulness"),
        "avg_answer_relevance":   avg("answer_relevance"),
        "refusal_accuracy":       avg("refusal_correct"),
        "oos_refusal_rate":        avg("refusal_correct", oos_rows),
        "in_scope_acceptance":     avg("refusal_correct", non_oos),
        "avg_ttft_ms":              avg("ttft_ms"),
        "avg_total_latency_ms":     avg("total_latency_ms"),
        "avg_retrieval_latency_ms": avg("retrieval_latency_ms"),
        "avg_pipeline_latency_ms":  avg("pipeline_latency_ms"),
        "avg_context_chars":        avg("context_chars"),
        "avg_output_tokens":        avg("output_tokens_approx"),
        "total_embed_cost_usd":     None,
        "chunk_mode":               rows[0]["chunk_mode"] if rows else "",
        "expand_on":                rows[0]["expand_on"] if rows else 0,
        "top_k":                    rows[0]["top_k"] if rows else 0,
        "max_context":              rows[0].get("max_context", 12) if rows else 12,
        "max_output_tokens":        rows[0].get("max_output_tokens", 600) if rows else 600,
        "retrieval_mode":           rows[0].get("retrieval_mode", "dense") if rows else "dense",
    }


# ── Save results ──────────────────────────────────────────────────────────────

def save_results(rows: list[dict[str, Any]], run_id: str) -> None:
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    stem = f"{run_id}_{ts}"

    # Per-question CSV — dùng DETAIL_FIELDNAMES cố định, bỏ qua field thừa,
    # điền "" cho field thiếu (backward-compat với checkpoint cũ)
    csv_path = RESULTS_DIR / f"{stem}_detail.csv"
    if rows:
        all_keys = set().union(*[r.keys() for r in rows])
        fieldnames = [f for f in DETAIL_FIELDNAMES if f in all_keys]
        extra = [k for k in all_keys if k not in DETAIL_FIELDNAMES]
        if extra:
            fieldnames += sorted(extra)
        with csv_path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            for row in rows:
                filled = {k: row.get(k, "") for k in fieldnames}
                writer.writerow(filled)
        print(f"[SAVED] {csv_path}")

    # Summary JSON
    summary = aggregate(rows)
    summary["run_id"] = run_id
    summary["timestamp"] = ts
    json_path = RESULTS_DIR / f"{stem}_summary.json"
    json_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[SAVED] {json_path}")

    # Bootstrap 95% CI + stats report (cho Ch4 luận văn)
    stats_path = eval_stats.write_stats_report(rows, run_id, RESULTS_DIR)
    print(f"[SAVED] {stats_path}")

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

def run_single(
    top_k: int | None = None,
    *,
    resume: bool = True,
    workers: int = 1,
) -> list[dict[str, Any]]:
    items = load_eval_set()
    if rag.CHUNK_MODE != "semantic":
        raise ValueError("Fixed chunking needs a separately built source-judged dataset/index; do not reuse semantic qrels")
    _gold_snapshot()
    k = top_k or rag.TOP_K
    run_id = make_run_id(k)

    done_rows = load_checkpoint_rows(run_id) if resume else []
    done_ids = {str(r["id"]) for r in done_rows}
    pending = [item for item in items if item["id"] not in done_ids]

    judge_backend    = f"Cursor ({CURSOR_MODEL})" if USE_CURSOR_JUDGE    else f"Gemini ({rag.LLM_MODEL})"
    generate_backend = f"Cursor ({CURSOR_MODEL})" if USE_CURSOR_GENERATE else f"Gemini ({rag.LLM_MODEL})"
    print(f"\n=== Eval run: {run_id} | {len(items)} questions ===")
    print(f"  Judge:      {judge_backend}")
    print(f"  Generation: {generate_backend}")
    print(f"  Workers:    {workers}")
    if done_ids:
        print(f"  [RESUME] {len(done_ids)} câu đã xong, còn {len(pending)} câu")
    print(
        f"  Rate limit: GEMINI_EMBED_MIN_INTERVAL_SEC={os.environ.get('GEMINI_EMBED_MIN_INTERVAL_SEC', '0.5')} "
        f"EMBED_REQUEST_DELAY_MS={os.environ.get('EMBED_REQUEST_DELAY_MS')}"
    )
    if workers > 1:
        print(f"  [PARALLEL] {workers} workers × embed serialized via global rate limiter")

    rows_by_id: dict[str, dict[str, Any]] = {str(r["id"]): r for r in done_rows}
    quota_hit = threading.Event()
    _done_count = [len(done_ids)]
    _print_lock = threading.Lock()

    def _eval_one(item: dict[str, Any]) -> dict[str, Any] | None:
        if quota_hit.is_set():
            return None
        with _print_lock:
            _done_count[0] += 1
            print(f"  [{_done_count[0]:02d}/{len(items)}] {item['id']} ({item['category']}) ...", flush=True)
        try:
            return evaluate_one(item, k)
        except QuotaExhaustedError:
            quota_hit.set()
            return None
        except Exception as e:  # noqa: BLE001
            if is_quota_error(e):
                quota_hit.set()
                return None
            print(f"    [WARN] {item['id']} error: {e}")
            return None

    if workers <= 1:
        # Sequential path (original behaviour)
        for item in pending:
            if quota_hit.is_set():
                break
            row = _eval_one(item)
            if row is not None:
                append_checkpoint(run_id, row)
                rows_by_id[str(row["id"])] = row
    else:
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
            fut_map = {pool.submit(_eval_one, item): item for item in pending}
            for fut in concurrent.futures.as_completed(fut_map):
                row = fut.result()
                if row is not None:
                    append_checkpoint(run_id, row)
                    rows_by_id[str(row["id"])] = row

    if quota_hit.is_set():
        print_quota_pause(run_id, len(items))
        sys.exit(EXIT_QUOTA)

    rows = [rows_by_id[item["id"]] for item in items if item["id"] in rows_by_id]
    if len(rows) >= len(items):
        save_results(rows, run_id)
    return rows


def run_ablation(workers: int = 1) -> None:
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
    retrieval_mode = os.environ.get("RETRIEVAL_MODE", "dense").lower()
    os.environ["RETRIEVAL_MODE"] = retrieval_mode
    rag.RETRIEVAL_MODE = retrieval_mode
    configs = [cfg for cfg in configs if cfg["CHUNK_MODE"] == "semantic"]
    print("[NOTE] Fixed chunking omitted until separately indexed and judged.")
    for cfg in configs:
        os.environ["CHUNK_MODE"] = cfg["CHUNK_MODE"]
        os.environ["EXPAND_ON"]  = cfg["EXPAND_ON"]
        os.environ["TOP_K"]      = cfg["TOP_K"]
        apply_env_config()

        run_id = make_run_id(int(cfg["TOP_K"]))
        if config_is_complete(run_id):
            rows = load_checkpoint_rows(run_id)
            print(f"\n[SKIP CONFIG] {run_id} đã đủ {len(rows)} câu — bỏ qua eval")
            summaries.append(aggregate(rows))
            continue

        print(f"\n{'='*60}")
        print(
            f"CONFIG: CHUNK_MODE={cfg['CHUNK_MODE']} EXPAND_ON={cfg['EXPAND_ON']} "
            f"TOP_K={cfg['TOP_K']} RETRIEVAL_MODE={retrieval_mode}"
        )
        print(f"{'='*60}")

        rows = run_single(top_k=int(cfg["TOP_K"]), resume=True, workers=workers)
        summaries.append(aggregate(rows))

    save_ablation_table(summaries)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="TLU RAG Evaluation Harness")
    parser.add_argument("--ablation", action="store_true",
                        help="Run full 12-config ablation matrix")
    parser.add_argument("--top-k", type=int, default=None,
                        help="Override TOP_K for single run")
    parser.add_argument("--resume", action="store_true", default=True,
                        help="Skip questions already in checkpoint (default: on)")
    parser.add_argument("--no-resume", action="store_true",
                        help="Ignore checkpoint and start fresh")
    parser.add_argument("--workers", type=int,
                        default=int(os.environ.get("EVAL_WORKERS", "3")),
                        help="Parallel workers (default: EVAL_WORKERS env or 3)")
    parser.add_argument("--eval-set", type=str, default=None,
                        help="Path to eval JSONL (default: eval/eval_set.jsonl)")
    parser.add_argument("--max-context", type=int, default=None,
                        help="Override MAX_CONTEXT for this run")
    parser.add_argument("--max-output-tokens", type=int, default=None,
                        help="Override MAX_OUTPUT_TOKENS for this run")
    args = parser.parse_args()

    if args.eval_set:
        p = Path(args.eval_set).resolve()
        if not p.exists():
            print(f"[ERROR] Eval set not found: {p}")
            sys.exit(1)
        globals()["_eval_set_override"] = p
    if args.max_context is not None:
        os.environ["MAX_CONTEXT"] = str(args.max_context)
    if args.max_output_tokens is not None:
        os.environ["MAX_OUTPUT_TOKENS"] = str(args.max_output_tokens)
    apply_env_config()

    # Kiểm tra API key cho retrieval/embedding (luôn cần Gemini embed)
    gemini_key = (os.environ.get("GEMINI_API_KEY") or "").strip()
    if not gemini_key:
        print("[ERROR] GEMINI_API_KEY chưa có (cần cho retrieval/embedding).")
        print(f"  → Sửa file: {_repo_root / '.env'}")
        sys.exit(1)

    # Thông báo backend đang dùng
    if USE_CURSOR_JUDGE or USE_CURSOR_GENERATE:
        print(f"[INFO] Cursor SDK v{_CURSOR_SDK_AVAILABLE and 'available' or 'N/A'} — "
              f"judge={USE_CURSOR_JUDGE} generate={USE_CURSOR_GENERATE} model={CURSOR_MODEL}")
    else:
        if not _CURSOR_SDK_AVAILABLE:
            print("[INFO] cursor-sdk không có — dùng Gemini cho cả judge và generation.")
        elif not CURSOR_API_KEY:
            print("[INFO] CURSOR_API_KEY chưa đặt — dùng Gemini cho cả judge và generation.")
        else:
            print("[INFO] Dùng Gemini cho judge và generation (CURSOR_JUDGE/CURSOR_GENERATE chưa bật).")

    if args.ablation:
        run_ablation(workers=args.workers)
    else:
        run_single(top_k=args.top_k, resume=not args.no_resume, workers=args.workers)
