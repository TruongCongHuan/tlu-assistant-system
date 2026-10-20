"""Cutoff-explicit retrieval metrics against versioned evidence judgments."""
from __future__ import annotations

import math


def retrieval_metrics(ids: list[str], grades: dict[str, int], *, k: int = 5,
                      answerable: bool = True, groups: dict[str, list[str]] | None = None,
                      required_groups: list[str] | None = None) -> dict[str, float | None]:
    if k < 1:
        raise ValueError("k must be positive")
    names = [f"hit@{j}" for j in sorted({1, min(3, k), k})]
    names += [f"mrr@{k}", f"ndcg@{k}", f"precision@{k}", f"recall@{k}", "evidence_coverage", "all_evidence"]
    if not answerable:
        return dict.fromkeys(names)
    relevant = {cid for cid, grade in grades.items() if grade >= 2}
    if not relevant:
        raise ValueError("Answerable query has no directly supporting evidence")
    # A duplicated chunk cannot earn gain twice or displace the metric denominator.
    unique = list(dict.fromkeys(ids))
    top = unique[:k]
    out: dict[str, float | None] = {}
    for j in sorted({1, min(3, k), k}):
        out[f"hit@{j}"] = float(any(cid in relevant for cid in unique[:j]))
    out[f"mrr@{k}"] = next((1.0 / rank for rank, cid in enumerate(top, 1) if cid in relevant), 0.0)
    gains = [(2 ** grades.get(cid, 0) - 1) for cid in top]
    dcg = sum(gain / math.log2(rank + 1) for rank, gain in enumerate(gains, 1))
    ideal = sorted((2 ** grade - 1 for grade in grades.values()), reverse=True)[:k]
    idcg = sum(gain / math.log2(rank + 1) for rank, gain in enumerate(ideal, 1))
    out[f"ndcg@{k}"] = dcg / idcg if idcg else 0.0
    found = len(set(top) & relevant)
    out[f"precision@{k}"] = found / k
    out[f"recall@{k}"] = found / len(relevant)
    required = set(required_groups or [])
    covered = set().union(*(set((groups or {}).get(cid, [])) for cid in top)) if top else set()
    out["evidence_coverage"] = len(covered & required) / len(required) if required else None
    out["all_evidence"] = float(required <= covered) if required else None
    return out


def candidate_metrics(ids: list[str], grades: dict[str, int], answerable: bool) -> dict[str, float | None]:
    if not answerable:
        return {"candidate_hit": None, "candidate_recall": None}
    gold = {cid for cid, grade in grades.items() if grade >= 2}
    if not gold:
        raise ValueError("Missing gold evidence")
    found = len(set(ids) & gold)
    return {"candidate_hit": float(found > 0), "candidate_recall": found / len(gold)}
