#!/usr/bin/env python3
"""Tóm tắt feedback RAG từ data/rag_feedback/ratings.jsonl."""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path


def load_jsonl(path: Path) -> list[dict]:
    rows: list[dict] = []
    if not path.is_file():
        return rows
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        rows.append(json.loads(line))
    return rows


def summarize(rows: list[dict]) -> dict:
    ratings = Counter(r.get("rating") for r in rows)
    down_samples = [
        {
            "id": r.get("id"),
            "question": (r.get("question") or "")[:160],
            "answer_preview": (r.get("answer") or "")[:160],
            "at": r.get("at"),
        }
        for r in rows
        if r.get("rating") == "down"
    ][:10]
    return {
        "total": len(rows),
        "up": ratings.get("up", 0),
        "down": ratings.get("down", 0),
        "down_samples": down_samples,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=Path(__file__).resolve().parents[2] / "data",
        help="Root data dir (STORAGE_BACKEND=file)",
    )
    args = parser.parse_args()

    path = args.data_dir / "rag_feedback" / "ratings.jsonl"
    rows = load_jsonl(path)
    report = summarize(rows)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if not rows:
        print(f"[INFO] No feedback yet at {path}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
