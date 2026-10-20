"""Ranking operations shared by the service and reproducible benchmarks."""
from __future__ import annotations

from typing import Any


def deduplicate_best(hits: list[dict[str, Any]]) -> list[dict[str, Any]]:
    best: dict[str, dict[str, Any]] = {}
    for hit in hits:
        key = str(hit["id"])
        if key not in best or hit["score"] > best[key]["score"]:
            best[key] = dict(hit)
    return sorted(best.values(), key=lambda h: (-h["score"], str(h["id"])))


def rrf_fuse(dense: list[dict[str, Any]], sparse: list[dict[str, Any]], *,
             k: int = 60, dense_weight: float = 0.7,
             sparse_weight: float = 0.3) -> list[dict[str, Any]]:
    if k <= 0 or min(dense_weight, sparse_weight) < 0 or dense_weight + sparse_weight <= 0:
        raise ValueError("Invalid RRF weights or rank constant")
    combined: dict[str, dict[str, Any]] = {}
    for hits, weight, name in [(dense, dense_weight, "dense"), (sparse, sparse_weight, "bm25")]:
        seen: set[str] = set()
        for rank, hit in enumerate(hits, 1):
            key = str(hit["id"])
            if key in seen or weight == 0:
                continue
            seen.add(key)
            entry = combined.setdefault(key, {**hit, "score": 0.0, "score_type": "rrf"})
            entry[name + "_score"] = float(hit["score"])
            entry[name + "_rank"] = rank
            entry["score"] += weight / (k + rank)
    return sorted(combined.values(), key=lambda h: (-h["score"], str(h["id"])))


def candidate_hash(hits: list[dict[str, Any]]) -> str:
    import hashlib
    import json
    # Include order, scores and text to detect accidental pool changes.
    payload = [(h["id"], h["text"], h["score"]) for h in hits]
    return hashlib.sha256(json.dumps(payload, ensure_ascii=False).encode()).hexdigest()
