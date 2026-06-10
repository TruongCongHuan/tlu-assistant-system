#!/usr/bin/env python3
"""Light sweep for latency/cost tuning on top of C1 (semantic, exp=1, dense).

Runs a stratified 12-question subset and picks the best config that meets
MIN_ANSWER_RELEVANCE while minimizing pipeline latency + cost proxy.

Usage (from repo root):
    .venv/bin/python services/rag-api/eval/sweep_latency_cost.py
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

_here = Path(__file__).resolve().parent
_repo = _here.parent.parent.parent
sys.path.insert(0, str(_here.parent))

from dotenv import load_dotenv

load_dotenv(_repo / ".env", override=True)

# Import after dotenv so run_eval picks up keys
from eval.run_eval import (  # noqa: E402
    RESULTS_DIR,
    aggregate,
    apply_env_config,
    make_run_id,
    run_single,
)

LIGHT_EVAL = _here / "eval_set_light.jsonl"
MIN_ANSWER_RELEVANCE = float(os.environ.get("MIN_ANSWER_RELEVANCE", "0.85"))

# Fixed C1 base; vary secondary knobs only
CONFIGS = [
    {"label": "C1-baseline", "TOP_K": "8",  "MAX_CONTEXT": "12", "MAX_OUTPUT_TOKENS": "600"},
    {"label": "LC-1",        "TOP_K": "8",  "MAX_CONTEXT": "8",  "MAX_OUTPUT_TOKENS": "600"},
    {"label": "LC-2",        "TOP_K": "8",  "MAX_CONTEXT": "8",  "MAX_OUTPUT_TOKENS": "400"},
    {"label": "LC-3",        "TOP_K": "5",  "MAX_CONTEXT": "8",  "MAX_OUTPUT_TOKENS": "400"},
    {"label": "LC-4",        "TOP_K": "8",  "MAX_CONTEXT": "10", "MAX_OUTPUT_TOKENS": "500"},
]


def cost_proxy(summary: dict) -> float:
    """Lower is better: context size + output length."""
    return summary["avg_context_chars"] + summary["avg_output_tokens"] * 4


def rank_key(summary: dict) -> tuple[float, float, float]:
    return (
        summary["avg_pipeline_latency_ms"],
        cost_proxy(summary),
        -summary["avg_answer_relevance"],
    )


def main() -> None:
    os.environ.setdefault("CHUNK_MODE", "semantic")
    os.environ.setdefault("EXPAND_ON", "1")
    os.environ.setdefault("RETRIEVAL_MODE", "dense")
    os.environ.setdefault("EVAL_WORKERS", "1")
    os.environ["EVAL_SET_PATH"] = str(LIGHT_EVAL)

    # Patch eval set path in run_eval module
    import eval.run_eval as run_eval_mod  # noqa: E402

    run_eval_mod._eval_set_override = LIGHT_EVAL

    summaries: list[dict] = []

    print(f"\n=== Latency/Cost sweep | {len(CONFIGS)} configs | eval={LIGHT_EVAL.name} ===")
    print(f"  MIN_ANSWER_RELEVANCE = {MIN_ANSWER_RELEVANCE}")

    for cfg in CONFIGS:
        os.environ["TOP_K"] = cfg["TOP_K"]
        os.environ["MAX_CONTEXT"] = cfg["MAX_CONTEXT"]
        os.environ["MAX_OUTPUT_TOKENS"] = cfg["MAX_OUTPUT_TOKENS"]
        apply_env_config()

        run_id = make_run_id(int(cfg["TOP_K"]))
        print(f"\n{'='*60}")
        print(
            f"CONFIG {cfg['label']}: TOP_K={cfg['TOP_K']} "
            f"MAX_CONTEXT={cfg['MAX_CONTEXT']} MAX_OUTPUT_TOKENS={cfg['MAX_OUTPUT_TOKENS']}"
        )
        print(f"  run_id={run_id}")
        print(f"{'='*60}")

        rows = run_single(top_k=int(cfg["TOP_K"]), resume=True, workers=1)
        summary = aggregate(rows)
        summary["label"] = cfg["label"]
        summary["run_id"] = run_id
        summary["cost_proxy"] = round(cost_proxy(summary), 1)
        summaries.append(summary)

    eligible = [
        s for s in summaries
        if s["avg_answer_relevance"] >= MIN_ANSWER_RELEVANCE
    ]
    if not eligible:
        print(f"\n[WARN] Không cấu hình nào đạt Ans. Rel. >= {MIN_ANSWER_RELEVANCE}")
        eligible = summaries

    winner = min(eligible, key=rank_key)

    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    out_json = RESULTS_DIR / f"latency_cost_sweep_{ts}.json"
    out_md = RESULTS_DIR / f"latency_cost_sweep_{ts}.md"

    payload = {
        "timestamp": ts,
        "min_answer_relevance": MIN_ANSWER_RELEVANCE,
        "eval_set": str(LIGHT_EVAL),
        "n_questions": summaries[0]["n_total"] if summaries else 0,
        "configs": summaries,
        "winner": winner,
    }
    out_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    cols = [
        "label", "top_k", "max_context", "max_output_tokens",
        "avg_answer_relevance", "avg_faithfulness", "avg_hit_rate_at_k",
        "avg_pipeline_latency_ms", "avg_retrieval_latency_ms", "avg_total_latency_ms",
        "avg_context_chars", "avg_output_tokens", "cost_proxy",
    ]
    lines = [
        "# Latency/Cost sweep (C1 base, eval nhẹ 12 câu)",
        "",
        f"- Ngưỡng Ans. Rel. tối thiểu: **{MIN_ANSWER_RELEVANCE}**",
        f"- Cấu hình đề xuất: **{winner['label']}** "
        f"(TOP_K={winner['top_k']}, MAX_CONTEXT={winner['max_context']}, "
        f"MAX_OUTPUT_TOKENS={winner['max_output_tokens']})",
        "",
        "| " + " | ".join(cols) + " |",
        "| " + " | ".join(["---"] * len(cols)) + " |",
    ]
    for s in summaries:
        mark = " **" if s["label"] == winner["label"] else ""
        row = "| " + " | ".join(
            f"{s.get(c, '')}{mark}" if c == "label" else str(s.get(c, ""))
            for c in cols
        ) + " |"
        lines.append(row)

    out_md.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"\n[SAVED] {out_json}")
    print(f"[SAVED] {out_md}")
    print(f"\n── Winner: {winner['label']} ──")
    for k in cols:
        if k != "label":
            print(f"  {k:<28} {winner.get(k, '')}")


if __name__ == "__main__":
    main()
