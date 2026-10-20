"""Statistical helpers for RAG eval results (bootstrap CI, McNemar)."""
from __future__ import annotations

import json
import math
import random
from pathlib import Path
from typing import Any


def bootstrap_mean_ci(
    values: list[float],
    *,
    n_resamples: int = 2000,
    ci: float = 0.95,
    seed: int = 42,
) -> dict[str, float]:
    """Bootstrap percentile CI for the mean."""
    clean = [float(v) for v in values if isinstance(v, (int, float)) and v >= 0]
    if not clean:
        return {"mean": 0.0, "ci_low": 0.0, "ci_high": 0.0, "n": 0}

    rng = random.Random(seed)
    n = len(clean)
    means: list[float] = []
    for _ in range(n_resamples):
        sample = [clean[rng.randrange(n)] for _ in range(n)]
        means.append(sum(sample) / n)

    means.sort()
    alpha = 1.0 - ci
    lo_idx = max(0, int((alpha / 2) * n_resamples) - 1)
    hi_idx = min(n_resamples - 1, int((1 - alpha / 2) * n_resamples))
    return {
        "mean": round(sum(clean) / n, 4),
        "ci_low": round(means[lo_idx], 4),
        "ci_high": round(means[hi_idx], 4),
        "n": n,
    }


def mcnemar_test(a_correct: list[int], b_correct: list[int]) -> dict[str, Any]:
    """McNemar test for paired binary outcomes (e.g. hit@k config A vs B)."""
    if len(a_correct) != len(b_correct):
        raise ValueError("McNemar requires paired samples of equal length")

    b01 = sum(1 for a, b in zip(a_correct, b_correct) if a == 0 and b == 1)
    b10 = sum(1 for a, b in zip(a_correct, b_correct) if a == 1 and b == 0)
    n_discord = b01 + b10
    if n_discord == 0:
        return {"b01": 0, "b10": 0, "chi2": 0.0, "p_approx": 1.0}

    chi2 = (abs(b01 - b10) - 1) ** 2 / n_discord if n_discord else 0.0
    # Normal approx to chi-square(1) for p-value
    p_approx = math.erfc(math.sqrt(max(chi2, 0.0)) / math.sqrt(2))
    return {
        "b01": b01,
        "b10": b10,
        "chi2": round(chi2, 4),
        "p_approx": round(p_approx, 4),
    }


def paired_mean_diff_ci(
    a_values: list[float],
    b_values: list[float],
    *,
    n_resamples: int = 2000,
    ci: float = 0.95,
    seed: int = 42,
) -> dict[str, float]:
    """Bootstrap CI for mean(B - A) on paired samples."""
    if len(a_values) != len(b_values):
        raise ValueError("Paired diff requires equal-length samples")

    diffs = [
        float(b) - float(a)
        for a, b in zip(a_values, b_values)
        if isinstance(a, (int, float)) and isinstance(b, (int, float)) and a >= 0 and b >= 0
    ]
    if not diffs:
        return {"mean_diff": 0.0, "ci_low": 0.0, "ci_high": 0.0, "n": 0}

    rng = random.Random(seed)
    n = len(diffs)
    boot: list[float] = []
    for _ in range(n_resamples):
        sample = [diffs[rng.randrange(n)] for _ in range(n)]
        boot.append(sum(sample) / n)
    boot.sort()
    alpha = 1.0 - ci
    lo_idx = max(0, int((alpha / 2) * n_resamples) - 1)
    hi_idx = min(n_resamples - 1, int((1 - alpha / 2) * n_resamples))
    return {
        "mean_diff": round(sum(diffs) / n, 4),
        "ci_low": round(boot[lo_idx], 4),
        "ci_high": round(boot[hi_idx], 4),
        "n": n,
    }


def summarize_run(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Bootstrap 95% CI for key metrics on one eval run."""
    metrics = [
        "context_precision",
        "hit_rate_at_k",
        "mrr",
        "ndcg",
        "faithfulness",
        "answer_relevance",
    ]
    out: dict[str, Any] = {"n": len(rows), "metrics": {}}
    for m in metrics:
        vals = [r[m] for r in rows if isinstance(r.get(m), (int, float))]
        out["metrics"][m] = bootstrap_mean_ci(vals)
    return out


def write_stats_report(
    rows: list[dict[str, Any]],
    run_id: str,
    results_dir: Path,
) -> Path:
    """Write JSON stats report next to eval CSV."""
    report = {
        "run_id": run_id,
        "summary": summarize_run(rows),
    }
    path = results_dir / f"{run_id}_stats.json"
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def compare_runs(
    rows_a: list[dict[str, Any]],
    rows_b: list[dict[str, Any]],
    *,
    label_a: str,
    label_b: str,
) -> dict[str, Any]:
    """Compare two paired runs (same question ids) — McNemar on hit@k + diff CI."""
    by_a = {str(r["id"]): r for r in rows_a if r.get("category") != "out_of_scope"}
    by_b = {str(r["id"]): r for r in rows_b if r.get("category") != "out_of_scope"}
    common = sorted(set(by_a) & set(by_b))
    if not common:
        return {"error": "no overlapping question ids"}

    hit_a = [int(float(by_a[i].get("hit_rate_at_k", 0))) for i in common]
    hit_b = [int(float(by_b[i].get("hit_rate_at_k", 0))) for i in common]
    faith_a = [float(by_a[i].get("faithfulness", 0)) for i in common]
    faith_b = [float(by_b[i].get("faithfulness", 0)) for i in common]

    return {
        "label_a": label_a,
        "label_b": label_b,
        "n_paired": len(common),
        "hit_rate_at_k_mcnemar": mcnemar_test(hit_a, hit_b),
        "faithfulness_diff": paired_mean_diff_ci(faith_a, faith_b),
    }
