"""In-memory BM25 index persisted alongside Chroma for hybrid retrieval."""
from __future__ import annotations

import pickle
import re
from pathlib import Path
from typing import Any

from rank_bm25 import BM25Okapi

_TOKEN_RE = re.compile(r"[\w]+", flags=re.UNICODE)


def tokenize(text: str) -> list[str]:
    return _TOKEN_RE.findall(text.lower())


def index_path(data_dir: Path) -> Path:
    return data_dir / "bm25_index.pkl"


def rebuild_from_collection(coll: Any, data_dir: Path) -> int:
    """Build BM25 index from all documents in a Chroma collection."""
    data = coll.get(include=["documents", "metadatas"])
    ids = data.get("ids") or []
    docs = data.get("documents") or []
    metas = data.get("metadatas") or []

    if not ids:
        path = index_path(data_dir)
        if path.exists():
            path.unlink()
        return 0

    tokenized = [tokenize(d or "") for d in docs]
    bm25 = BM25Okapi(tokenized)
    payload = {
        "ids": ids,
        "documents": docs,
        "metadatas": metas,
        "bm25": bm25,
    }
    data_dir.mkdir(parents=True, exist_ok=True)
    index_path(data_dir).write_bytes(pickle.dumps(payload))
    return len(ids)


def load(data_dir: Path) -> dict[str, Any] | None:
    path = index_path(data_dir)
    if not path.exists():
        return None
    return pickle.loads(path.read_bytes())


def search(
    query: str,
    data_dir: Path,
    *,
    top_k: int,
    doc_id: str | None = None,
) -> list[dict[str, Any]]:
    """Return top-k chunks ranked by BM25 score."""
    payload = load(data_dir)
    if not payload:
        return []

    bm25: BM25Okapi = payload["bm25"]
    ids: list[str] = payload["ids"]
    docs: list[str] = payload["documents"]
    metas: list[dict[str, Any]] = payload["metadatas"]

    scores = bm25.get_scores(tokenize(query))
    ranked = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)

    out: list[dict[str, Any]] = []
    for i in ranked:
        if scores[i] <= 0:
            continue
        meta = metas[i] or {}
        if doc_id and meta.get("doc_id") != doc_id:
            continue
        out.append({
            "id": ids[i],
            "text": docs[i],
            "meta": meta,
            "score": float(scores[i]),
        })
        if len(out) >= top_k:
            break
    return out
