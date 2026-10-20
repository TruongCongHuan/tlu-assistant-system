"""Freeze the shared semantic corpus and map authored, quoted evidence to chunks.

No heading matching or model-generated automatic relevance labels are used.
Source spans are an agent-authored pilot, not independently human-adjudicated qrels.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

SERVICE = Path(__file__).resolve().parents[1]
ROOT = SERVICE.parents[1]
sys.path.insert(0, str(SERVICE))
from app.chunking import chunk_text_semantic

DATASET = SERVICE / "eval/datasets/retrieval_v1"
CORPUS = ROOT / "output_md/guide_book_k38_pymupdf.md"


def digest(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows))


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def build() -> dict:
    raw = CORPUS.read_bytes()
    sha = digest(raw)
    chunks = chunk_text_semantic(raw.decode(), "k38-" + sha[:12], CORPUS.name)
    for chunk in chunks:
        chunk["id"] = f"k38-v1:{chunk['meta']['chunk_index']}:{digest(chunk['text'].encode())[:16]}"
    specs = read_jsonl(DATASET / "evidence_queries.jsonl")
    qrels, queries = [], []
    normalized_corpus = normalize(raw.decode())
    for spec in specs:
        query = {k: v for k, v in spec.items() if k != "evidence"}
        query["required_evidence_groups"] = []
        for index, evidence in enumerate(spec.get("evidence", []), 1):
            quote = normalize(evidence["quote"])
            if len(quote) < 20 or quote not in normalized_corpus:
                raise ValueError(f"Missing/short source quote: {spec['query_id']}: {quote[:90]}")
            group = evidence.get("group", f"{spec['intent_group']}:E{index}")
            query["required_evidence_groups"].append(group)
            matches = [c for c in chunks if quote in normalize(c["text"])
                       and evidence.get("heading_contains", "") in c["meta"]["heading_path"]]
            if not matches:
                raise ValueError(f"Evidence crosses chunk boundary: {spec['query_id']}")
            for chunk in matches:
                qrels.append({"query_id": spec["query_id"], "chunk_id": chunk["id"],
                              "relevance": 2, "evidence_group_id": group,
                              "source_span": evidence["quote"],
                              "rationale": "Explicit authored source evidence; equivalent overlapping chunks accepted"})
        query["required_evidence_groups"] = sorted(set(query["required_evidence_groups"]))
        if bool(query["required_evidence_groups"]) != query["answerable"]:
            raise ValueError(f"Evidence/answerability mismatch: {query['query_id']}")
        queries.append(query)
    if len({q["query_id"] for q in queries}) != len(queries):
        raise ValueError("Duplicate query ID")
    dev = {q["intent_group"] for q in queries if q["split"] == "dev"}
    test = {q["intent_group"] for q in queries if q["split"] == "test"}
    if dev & test:
        raise ValueError("Intent group leaked between splits")
    # Exact supporting chunks shared across splits invalidate the claim of evidence disjointness.
    dev_ids = {q["query_id"] for q in queries if q["split"] == "dev"}
    test_ids = {q["query_id"] for q in queries if q["split"] == "test"}
    dev_chunks = {r["chunk_id"] for r in qrels if r["query_id"] in dev_ids}
    test_chunks = {r["chunk_id"] for r in qrels if r["query_id"] in test_ids}
    write_jsonl(DATASET / "chunks.jsonl", chunks)
    write_jsonl(DATASET / "qrels.jsonl", qrels)
    for split in ["dev", "test"]:
        write_jsonl(DATASET / f"queries_{split}.jsonl", [q for q in queries if q["split"] == split])
    manifest = {"version": "retrieval_v1", "corpus_sha256": sha, "chunk_count": len(chunks),
                "source": str(CORPUS.relative_to(ROOT)), "chunking": "shared_semantic_v1",
                "chunk_size": 1200, "seed": 42, "qrels_complete": False,
                "annotation_status": "agent_authored_source_checked_pilot; human_review_pending",
                "unjudged_policy": "Metrics use known positive evidence; recall is known-gold recall, not exhaustive corpus recall",
                "shared_positive_chunks_between_splits": sorted(dev_chunks & test_chunks),
                "queries": {s: sum(q["split"] == s for q in queries) for s in ["dev", "test"]}}
    for name in ["evidence_queries.jsonl", "chunks.jsonl", "qrels.jsonl", "queries_dev.jsonl", "queries_test.jsonl"]:
        manifest[name + "_sha256"] = digest((DATASET / name).read_bytes())
    (DATASET / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    return manifest


def validate() -> dict:
    manifest = json.loads((DATASET / "manifest.json").read_text())
    if manifest["corpus_sha256"] != digest(CORPUS.read_bytes()):
        raise ValueError("Source corpus changed; rebuild/version qrels before running")
    for name in ["evidence_queries.jsonl", "chunks.jsonl", "qrels.jsonl", "queries_dev.jsonl", "queries_test.jsonl"]:
        if digest((DATASET / name).read_bytes()) != manifest[name + "_sha256"]:
            raise ValueError("Dataset hash mismatch: " + name)
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--validate", action="store_true")
    args = parser.parse_args()
    print(json.dumps(validate() if args.validate else build(), ensure_ascii=False, indent=2))
