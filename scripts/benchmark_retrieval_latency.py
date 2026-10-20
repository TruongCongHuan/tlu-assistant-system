"""Three complete cached-vector retrieval/rerank replays on the dev smoke subset.

Uses a completed dev run's exact config and records ANN replay differences.
This is a latency study, not extra independent quality observations.
"""
from __future__ import annotations

import argparse
import json
import os
import random
import resource
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SERVICE = ROOT / "services/rag-api"
sys.path.insert(0, str(SERVICE))
from app.bm25_index import tokenize
from app.retrieval import candidate_hash, rrf_fuse
from app.reranker import RerankerConfig, get_reranker
from eval.build_retrieval_dataset import DATASET, digest, read_jsonl, validate, write_jsonl
from eval.report_retrieval_benchmark import percentile, write_csv
from eval.run_retrieval_benchmark import MODES, OUT, cache_dir, dump, fingerprint, source_hashes


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reference-run", required=True, type=Path)
    parser.add_argument("--repetitions", type=int, default=3)
    args = parser.parse_args()
    if args.repetitions < 3:
        parser.error("Use at least three repetitions")
    reference = json.loads((args.reference_run / "manifest.json").read_text())
    if reference["split"] != "dev" or reference["smoke"] or not reference.get("finished_at"):
        raise ValueError("Reference must be a completed full dev run")
    dataset = validate()
    if reference["source_hashes"] != source_hashes() or reference["dataset_hash"] != fingerprint(dataset):
        raise ValueError("Reference code/dataset mismatch")
    import chromadb
    import numpy as np
    from chromadb.config import Settings
    from rank_bm25 import BM25Okapi
    config = reference["config"]
    directory = cache_dir(config, dataset)
    chunks = read_jsonl(DATASET / "chunks.jsonl")
    all_queries = read_jsonl(DATASET / "queries_dev.jsonl")
    indices = {q["query_id"]: i for i, q in enumerate(all_queries)}
    light = {q["id"] for q in read_jsonl(SERVICE / "eval/eval_set_light.jsonl")}
    queries = [q for q in all_queries if q["query_id"] in light]
    vectors = np.load(directory / "dev.npy")
    bm25 = BM25Okapi([tokenize(c["text"]) for c in chunks])
    by_id = {c["id"]: c for c in chunks}
    expected = {(r["query_id"], r["config"]): r["candidate_hash"]
                for r in read_jsonl(args.reference_run / "rankings.jsonl") if r["status"] == "ok"}
    expected_ids = {(r["query_id"], r["config"]): {h["id"] for h in r["hits"]}
                    for r in read_jsonl(args.reference_run / "candidates.jsonl")}
    client = chromadb.PersistentClient(path=str(directory / "chroma"), settings=Settings(anonymized_telemetry=False))
    collection = client.get_collection("retrieval_v1")
    os.environ["TORCH_NUM_THREADS"] = str(config["threads"])
    ranker = get_reranker(RerankerConfig(model=config["rerank_model"], revision=config["rerank_revision"],
                         device=config["device"], max_length=config["max_length"], batch_size=config["batch_size"],
                         quantize_int8=config.get("quantize_int8", False)))
    k = config["candidate_k"]

    def retrieve(query: dict, kind: str) -> tuple[list[dict], dict]:
        times = {"dense_ms": 0.0, "bm25_ms": 0.0, "fusion_ms": 0.0}
        dense, sparse = [], []
        if kind != "bm25":
            t = time.perf_counter()
            result = collection.query(query_embeddings=[vectors[indices[query["query_id"]]].tolist()],
                                      n_results=min(k, len(chunks)), include=["distances"])
            dense = [{**by_id[cid], "score": 1-float(distance)}
                     for cid, distance in zip(result["ids"][0], result["distances"][0])]
            times["dense_ms"] = (time.perf_counter()-t)*1000
        if kind != "dense":
            t = time.perf_counter()
            scores = bm25.get_scores(tokenize(query["question"]))
            order = sorted(range(len(chunks)), key=lambda i: (-scores[i], chunks[i]["id"]))
            sparse = [{**chunks[i], "score": float(scores[i])} for i in order if scores[i] > 0][:k]
            times["bm25_ms"] = (time.perf_counter()-t)*1000
        if kind == "hybrid":
            t = time.perf_counter()
            pool = rrf_fuse(dense, sparse, k=config["rrf_k"], dense_weight=1-config["bm25_weight"],
                            sparse_weight=config["bm25_weight"])[:k]
            times["fusion_ms"] = (time.perf_counter()-t)*1000
        else:
            pool = dense if kind == "dense" else sparse
        return pool, times

    warm, _ = retrieve(queries[0], "hybrid")
    ranker.rerank(queries[0]["question"], warm)
    rows = []
    for qi, query in enumerate(queries):
        for repeat in range(args.repetitions):
            modes = list(MODES)
            random.Random(config["seed"]+qi*args.repetitions+repeat).shuffle(modes)
            for mode in modes:
                kind, use_ce = MODES[mode]
                t = time.perf_counter()
                pool, times = retrieve(query, kind)
                validation_start = time.perf_counter()
                hash_matches = candidate_hash(pool) == expected[(query["query_id"], mode)]
                ids_match = {h["id"] for h in pool} == expected_ids[(query["query_id"], mode)]
                validation_seconds = time.perf_counter() - validation_start
                times["rerank_ms"] = 0.0
                if use_ce:
                    result, info = ranker.rerank(query["question"], pool)
                    times["rerank_ms"] = info["rerank_ms"]
                else:
                    result = pool
                final = result[:config["final_k"]]
                times["total_ms"] = (time.perf_counter()-t-validation_seconds)*1000
                rows.append({"query_id": query["query_id"], "config": mode, "repetition": repeat,
                             "candidate_count": len(pool), "final_count": len(final),
                             "candidate_hash_matches_reference": hash_matches,
                             "candidate_ids_match_reference": ids_match, **times})
        print(f"[LATENCY] {qi+1}/{len(queries)} {query['query_id']}", flush=True)
    summary = {}
    for mode in MODES:
        samples = [r for r in rows if r["config"] == mode]
        summary[mode] = {"n": len(samples),
                         "candidate_hash_mismatches": sum(not r["candidate_hash_matches_reference"] for r in samples),
                         "candidate_set_mismatches": sum(not r["candidate_ids_match_reference"] for r in samples),
                         **{name: {"p50": percentile([r[name] for r in samples], .5),
                                                        "p95": percentile([r[name] for r in samples], .95)}
                                                     for name in ["dense_ms", "bm25_ms", "fusion_ms", "rerank_ms", "total_ms"]}}
    output = ROOT / "docs/benchmarks" / ("latency_"+config["profile"]+"_"+datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"))
    output.mkdir(parents=True, exist_ok=False)
    write_csv(output / "samples.csv", rows)
    dump(output / "summary.json", summary)
    dump(output / "manifest.json", {"reference_run": str(args.reference_run), "config": config,
                                    "query_ids": [q["query_id"] for q in queries], "repetitions": args.repetitions,
                                    "dataset_hash": fingerprint(dataset), "source_hashes": source_hashes(),
                                    "script_sha256": digest(Path(__file__).read_bytes()),
                                    "measurement": "three full cached-vector retrieval/rerank replays; dev-only; randomized config order",
                                    "peak_process_rss_mb": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024})
    print("[LATENCY RESULT]", output, flush=True)


if __name__ == "__main__":
    main()
