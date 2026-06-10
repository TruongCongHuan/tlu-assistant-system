"""Re-score saved eval rows with a second judge (Composer) while keeping Gemini scores.

Reads checkpoint JSONL or detail CSV from a prior run_eval.py execution.
Preserves existing faithfulness / answer_relevance as faithfulness_gemini /
answer_relevance_gemini, then adds faithfulness_composer / answer_relevance_composer.

Usage (from repo root):
    python services/rag-api/eval/re_judge.py --checkpoint services/rag-api/eval/results/checkpoint_cmsemantic_exp1_k8_rmde.jsonl
    python services/rag-api/eval/re_judge.py --all-checkpoints
    python services/rag-api/eval/re_judge.py --input services/rag-api/eval/results/foo_detail.csv
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_here = Path(__file__).resolve().parent
_repo_root = _here.parent.parent.parent
sys.path.insert(0, str(_here.parent))

from dotenv import load_dotenv

load_dotenv(_repo_root / ".env", override=True)

import run_eval as ev  # noqa: E402

RESULTS_DIR = ev.RESULTS_DIR
COMPOSER_MODEL = os.environ.get("COMPOSER_JUDGE_MODEL", "composer-2.5").strip()
JUDGE_DELAY_SEC = float(os.environ.get("RE_JUDGE_DELAY_SEC", "1.0"))

GEMINI_FAITH = "faithfulness_gemini"
GEMINI_REL = "answer_relevance_gemini"
COMP_FAITH = "faithfulness_composer"
COMP_REL = "answer_relevance_composer"


def load_rows(path: Path) -> list[dict[str, Any]]:
    if path.name.startswith("checkpoint_") and path.suffix == ".jsonl":
        run_id = run_id_from_path(path)
        return ev.load_checkpoint_rows(run_id)

    if path.suffix == ".jsonl":
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

    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def run_id_from_path(path: Path) -> str:
    name = path.name
    if name.startswith("checkpoint_") and name.endswith(".jsonl"):
        return name[len("checkpoint_") : -len(".jsonl")]
    if name.endswith("_detail.csv"):
        stem = name[: -len("_detail.csv")]
        if "_" in stem and stem[-1].isdigit():
            # cmsemantic_exp1_k8_rmde_20260609T124154 -> drop timestamp suffix
            parts = stem.rsplit("_", 1)
            if parts[-1].startswith("20") and "T" in parts[-1]:
                return parts[0]
        return stem
    return path.stem


def re_judge_checkpoint_path(run_id: str) -> Path:
    return RESULTS_DIR / f"re_judge_{run_id}.jsonl"


def load_re_judge_done(run_id: str) -> dict[str, dict[str, float]]:
    path = re_judge_checkpoint_path(run_id)
    done: dict[str, dict[str, float]] = {}
    if not path.exists():
        return done
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            done[str(obj["id"])] = {
                COMP_FAITH: float(obj[COMP_FAITH]),
                COMP_REL: float(obj[COMP_REL]),
            }
    return done


def append_re_judge_done(run_id: str, row_id: str, scores: dict[str, float]) -> None:
    path = re_judge_checkpoint_path(run_id)
    with path.open("a", encoding="utf-8") as f:
        f.write(
            json.dumps(
                {"id": row_id, COMP_FAITH: scores[COMP_FAITH], COMP_REL: scores[COMP_REL]},
                ensure_ascii=False,
            )
            + "\n"
        )


def ensure_gemini_columns(row: dict[str, Any]) -> None:
    if GEMINI_FAITH not in row or row[GEMINI_FAITH] == "":
        row[GEMINI_FAITH] = row.get("faithfulness", "")
    if GEMINI_REL not in row or row[GEMINI_REL] == "":
        row[GEMINI_REL] = row.get("answer_relevance", "")


def composer_judge(row: dict[str, Any], model: str) -> dict[str, float]:
    prev_model = ev.CURSOR_MODEL
    ev.CURSOR_MODEL = model
    try:
        scores = ev._cursor_ai_judge(
            question=str(row.get("question", "")),
            context=str(row.get("retrieved_context", "")),
            answer=str(row.get("answer", "")),
            ground_truth=str(row.get("ground_truth", "")),
        )
        return {
            COMP_FAITH: scores["faithfulness"],
            COMP_REL: scores["answer_relevance"],
        }
    finally:
        ev.CURSOR_MODEL = prev_model


def aggregate_dual(rows: list[dict[str, Any]]) -> dict[str, Any]:
    base = ev.aggregate(rows)

    def avg(key: str) -> float:
        vals = [
            float(r[key])
            for r in rows
            if key in r and r[key] != "" and isinstance(r[key], (int, float, str))
        ]
        clean: list[float] = []
        for v in vals:
            try:
                fv = float(v)
            except (TypeError, ValueError):
                continue
            if fv >= 0:
                clean.append(fv)
        return round(sum(clean) / len(clean), 4) if clean else 0.0

    base["avg_faithfulness_gemini"] = avg(GEMINI_FAITH)
    base["avg_answer_relevance_gemini"] = avg(GEMINI_REL)
    base["avg_faithfulness_composer"] = avg(COMP_FAITH)
    base["avg_answer_relevance_composer"] = avg(COMP_REL)
    base["composer_judge_model"] = COMPOSER_MODEL
    return base


def save_dual_results(rows: list[dict[str, Any]], run_id: str) -> tuple[Path, Path]:
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    stem = f"{run_id}_dual_judge_{ts}"

    fieldnames = list(ev.DETAIL_FIELDNAMES)
    for col in (GEMINI_FAITH, GEMINI_REL, COMP_FAITH, COMP_REL):
        if col not in fieldnames:
            idx = fieldnames.index("answer_relevance") + 1
            fieldnames.insert(idx, col)

    csv_path = RESULTS_DIR / f"{stem}_detail.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in fieldnames})

    summary = aggregate_dual(rows)
    summary["run_id"] = run_id
    summary["timestamp"] = ts
    json_path = RESULTS_DIR / f"{stem}_summary.json"
    json_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return csv_path, json_path


def process_file(path: Path, *, model: str, resume: bool) -> None:
    rows = load_rows(path)
    if not rows:
        print(f"[SKIP] Empty: {path}")
        return

    run_id = run_id_from_path(path)
    done = load_re_judge_done(run_id) if resume else {}

    print(f"\n=== Re-judge: {run_id} ({len(rows)} rows) ===")
    print(f"  Input:   {path}")
    print(f"  Composer model: {model}")
    if done:
        print(f"  [RESUME] {len(done)} composer scores already done")

    for i, row in enumerate(rows, 1):
        ensure_gemini_columns(row)
        row_id = str(row["id"])

        if row_id in done:
            row[COMP_FAITH] = done[row_id][COMP_FAITH]
            row[COMP_REL] = done[row_id][COMP_REL]
            continue

        if COMP_FAITH in row and COMP_REL in row and row[COMP_FAITH] != "" and resume:
            continue

        print(f"  [{i:02d}/{len(rows)}] {row_id} composer judge ...", flush=True)
        scores = composer_judge(row, model)
        if scores[COMP_FAITH] < 0 or scores[COMP_REL] < 0:
            print(f"    [WARN] {row_id} judge failed, skipping checkpoint (retry on next run)")
            row[COMP_FAITH] = scores[COMP_FAITH]
            row[COMP_REL] = scores[COMP_REL]
            if JUDGE_DELAY_SEC > 0:
                time.sleep(JUDGE_DELAY_SEC)
            continue

        row[COMP_FAITH] = scores[COMP_FAITH]
        row[COMP_REL] = scores[COMP_REL]
        append_re_judge_done(run_id, row_id, scores)

        if JUDGE_DELAY_SEC > 0:
            time.sleep(JUDGE_DELAY_SEC)

    csv_path, json_path = save_dual_results(rows, run_id)
    print(f"[SAVED] {csv_path}")
    print(f"[SAVED] {json_path}")
    summary = aggregate_dual(rows)
    print(
        f"  Gemini    faith={summary['avg_faithfulness_gemini']} "
        f"rel={summary['avg_answer_relevance_gemini']}"
    )
    print(
        f"  Composer  faith={summary['avg_faithfulness_composer']} "
        f"rel={summary['avg_answer_relevance_composer']}"
    )


def build_ablation_table() -> None:
    summaries: list[dict[str, Any]] = []
    for path in sorted(RESULTS_DIR.glob("*_dual_judge_*_summary.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        summaries.append(data)

    if not summaries:
        print("[WARN] No dual_judge summary files found.")
        return

    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    cols = [
        "chunk_mode", "expand_on", "top_k", "retrieval_mode",
        "avg_context_precision", "avg_hit_rate_at_k", "avg_mrr", "avg_ndcg",
        "avg_faithfulness_gemini", "avg_answer_relevance_gemini",
        "avg_faithfulness_composer", "avg_answer_relevance_composer",
        "refusal_accuracy", "composer_judge_model",
    ]
    csv_path = RESULTS_DIR / f"ablation_dual_judge_{ts}.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        writer.writeheader()
        for s in summaries:
            writer.writerow({c: s.get(c, "") for c in cols})
    print(f"[SAVED] {csv_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Add Composer judge columns to saved eval rows")
    parser.add_argument("--input", type=str, help="Detail CSV or checkpoint JSONL")
    parser.add_argument("--checkpoint", type=str, help="Checkpoint JSONL from run_eval.py")
    parser.add_argument(
        "--all-checkpoints",
        action="store_true",
        help="Process every checkpoint_*.jsonl in results/",
    )
    parser.add_argument(
        "--composer-model",
        type=str,
        default=COMPOSER_MODEL,
        help=f"Cursor model slug for judge (default: {COMPOSER_MODEL})",
    )
    parser.add_argument("--no-resume", action="store_true", help="Ignore re_judge checkpoint")
    parser.add_argument(
        "--build-ablation",
        action="store_true",
        help="After processing, build ablation_dual_judge CSV from summaries",
    )
    args = parser.parse_args()

    if not ev._CURSOR_SDK_AVAILABLE:
        print("[ERROR] cursor-sdk chưa cài. pip install cursor-sdk")
        sys.exit(1)
    if not ev.CURSOR_API_KEY:
        print("[ERROR] CURSOR_API_KEY chưa có trong .env")
        sys.exit(1)

    targets: list[Path] = []
    if args.input:
        targets.append(Path(args.input).resolve())
    if args.checkpoint:
        targets.append(Path(args.checkpoint).resolve())
    if args.all_checkpoints:
        for cp in sorted(RESULTS_DIR.glob("checkpoint_*.jsonl")):
            run_id = run_id_from_path(cp)
            if ev.config_is_complete(run_id):
                targets.append(cp)
            else:
                print(f"[SKIP] Incomplete checkpoint: {cp.name}")

    if not targets:
        parser.error("Cần --input, --checkpoint, hoặc --all-checkpoints")

    seen: set[Path] = set()
    for path in targets:
        if path in seen or not path.exists():
            if not path.exists():
                print(f"[WARN] Not found: {path}")
            continue
        seen.add(path)
        process_file(path, model=args.composer_model, resume=not args.no_resume)

    if args.build_ablation or args.all_checkpoints:
        build_ablation_table()


if __name__ == "__main__":
    main()
