#!/usr/bin/env python3
"""Phân loại lỗi từ file *_detail.csv của run_eval.py."""
from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path


def classify_row(row: dict[str, str]) -> list[str]:
    tags: list[str] = []
    category = (row.get("category") or "").strip().lower()

    try:
        hit = float(row.get("hit_rate_at_k") or 0)
    except ValueError:
        hit = 0.0
    try:
        faith = float(row.get("faithfulness") or -1)
    except ValueError:
        faith = -1.0
    try:
        cp = float(row.get("context_precision") or 0)
    except ValueError:
        cp = 0.0
    try:
        refusal = int(float(row.get("refusal_correct") or 0))
    except ValueError:
        refusal = 0

    if hit <= 0 and category != "out_of_scope":
        tags.append("retrieval_miss")
    if faith >= 0 and faith < 0.5:
        tags.append("low_faithfulness")
    if cp < 0.3 and category != "out_of_scope":
        tags.append("low_context_precision")
    if category == "out_of_scope" and refusal == 0:
        tags.append("false_accept")
    if category != "out_of_scope" and refusal == 0:
        tags.append("false_refusal")

    if not tags:
        tags.append("ok")
    return tags


def load_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def summarize(rows: list[dict[str, str]]) -> dict:
    by_tag: Counter[str] = Counter()
    by_category: dict[str, Counter[str]] = defaultdict(Counter)
    examples: dict[str, list[dict[str, str]]] = defaultdict(list)

    for row in rows:
        tags = classify_row(row)
        for t in tags:
            by_tag[t] += 1
            by_category[row.get("category", "?")][t] += 1
            if t != "ok" and len(examples[t]) < 5:
                examples[t].append(
                    {
                        "id": row.get("id"),
                        "category": row.get("category"),
                        "question": (row.get("question") or "")[:200],
                        "hit_rate_at_k": row.get("hit_rate_at_k"),
                        "faithfulness": row.get("faithfulness"),
                        "context_precision": row.get("context_precision"),
                    }
                )

    return {
        "n_questions": len(rows),
        "tag_counts": dict(by_tag),
        "by_category": {k: dict(v) for k, v in by_category.items()},
        "examples": dict(examples),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Error analysis from eval detail CSV")
    parser.add_argument("detail_csv", type=Path, help="Path to *_detail.csv")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help="Write JSON report (default: alongside CSV)",
    )
    args = parser.parse_args()

    if not args.detail_csv.is_file():
        print(f"[ERROR] Not found: {args.detail_csv}", file=sys.stderr)
        return 1

    rows = load_csv(args.detail_csv)
    report = summarize(rows)
    out = args.output or args.detail_csv.with_name(
        args.detail_csv.stem.replace("_detail", "") + "_error_analysis.json"
    )
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"[SAVED] {out}")
    print(json.dumps(report["tag_counts"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
