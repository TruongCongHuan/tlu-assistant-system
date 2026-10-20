"""Retrieval-only benchmark with immutable datasets and paired candidate pools.

Embedding is a separate process/stage so a CPU need not retain two models in RAM.
Ranking latency is explicitly cached-query-vector replay, not live API latency.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.metadata
import json
import os
import platform
import resource
import random
import subprocess
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

SERVICE = Path(__file__).resolve().parents[1]
ROOT = SERVICE.parents[1]
sys.path.insert(0, str(SERVICE))
from app.retrieval import candidate_hash, rrf_fuse
from app.reranker import RerankerConfig, get_reranker
from eval.build_retrieval_dataset import DATASET, digest, read_jsonl, validate, write_jsonl
from eval.retrieval_metrics import candidate_metrics, retrieval_metrics

OUT = ROOT / "data/benchmarks/reranking"
CONFIG = SERVICE / "eval/benchmark_configs.json"
MODES = {"A": ("dense", False), "B": ("bm25", False), "C": ("hybrid", False),
         "D": ("dense", True), "E": ("hybrid", True)}


def fingerprint(value: object) -> str:
    return digest(json.dumps(value, sort_keys=True, ensure_ascii=False).encode())


def source_hashes() -> dict:
    paths = list((SERVICE / "app").glob("*.py")) + list((SERVICE / "eval").glob("*.py"))
    paths += list(SERVICE.glob("requirements*"))
    return {str(p.relative_to(ROOT)): digest(p.read_bytes()) for p in sorted(paths)}


def dump(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n")


def cache_dir(config: dict, manifest: dict) -> Path:
    fields = {k: config[k] for k in ["embedding_model", "embedding_revision", "embedding_max_length", "threads"]}
    return OUT / "embedding_cache" / fingerprint({"embedding": fields, "chunks": manifest["chunks.jsonl_sha256"]})[:20]


def embed(config: dict, split: str, manifest: dict) -> None:
    import numpy as np
    import torch
    from sentence_transformers import SentenceTransformer
    torch.set_num_threads(config["threads"])
    model = SentenceTransformer(config["embedding_model"], revision=config["embedding_revision"],
                                device=config["device"], trust_remote_code=False)
    model.max_seq_length = config["embedding_max_length"]
    chunks = read_jsonl(DATASET / "chunks.jsonl")
    queries = read_jsonl(DATASET / f"queries_{split}.jsonl")
    directory = cache_dir(config, manifest)
    directory.mkdir(parents=True, exist_ok=True)
    # Prevent silently mixing representations after an environment/library change.
    if (directory / "corpus.npy").exists():
        saved_vectors = np.load(directory / "corpus.npy")
        for index in sorted({0, len(chunks)//2, len(chunks)-1}):
            fresh = model.encode(chunks[index]["text"], normalize_embeddings=True, show_progress_bar=False)
            if not np.allclose(saved_vectors[index], fresh, atol=1e-5, rtol=1e-4):
                raise ValueError("Embedding representation changed; use a new cache/index and recompute all vectors")
        print("[VERIFIED] Fresh encoder agrees with cached corpus probes", flush=True)
    for kind, entries, field in [("corpus", chunks, "text"), (split, queries, "question")]:
        texts = [e[field] for e in entries]
        text_hash = fingerprint(texts)
        meta_path = directory / f"{kind}.json"
        path = directory / f"{kind}.npy"
        if path.exists() and meta_path.exists() and json.loads(meta_path.read_text())["text_hash"] == text_hash:
            print("[CACHE]", kind, flush=True)
            continue
        timings, vectors, truncated = [], [], 0
        partial = directory / f"{kind}.partial.npy"
        partial_meta = directory / f"{kind}.partial.json"
        if partial.exists() and partial_meta.exists():
            state = json.loads(partial_meta.read_text())
            saved = np.load(partial)
            if state["text_hash"] == text_hash and len(saved) == len(state["timings_ms"]):
                vectors = list(saved)
                timings = state["timings_ms"]
                truncated = state["truncated_inputs"]
                print(f"[RESUME EMBED] {kind}: {len(vectors)}/{len(texts)}", flush=True)
        completed = len(vectors)
        t0 = time.perf_counter()
        # Batch one gives observable per-input encoding times and bounded CPU memory.
        for i, text in enumerate(texts):
            if i < completed:
                continue
            token_count = len(model.tokenizer(text, truncation=False, verbose=False)["input_ids"])
            truncated += token_count > model.max_seq_length
            ts = time.perf_counter()
            vectors.append(model.encode(text, normalize_embeddings=True, show_progress_bar=False))
            timings.append((time.perf_counter() - ts) * 1000)
            if i % 20 == 0:
                np.save(partial, np.asarray(vectors, dtype=np.float32))
                dump(partial_meta, {"text_hash": text_hash, "timings_ms": timings,
                                    "truncated_inputs": truncated})
                print(f"[EMBED] {kind} {i + 1}/{len(texts)} elapsed={time.perf_counter()-t0:.1f}s", flush=True)
        np.save(path, np.asarray(vectors, dtype=np.float32))
        dump(meta_path, {"text_hash": text_hash, "ids": [e.get("query_id", e.get("id")) for e in entries],
                         "timings_ms": timings, "truncated_inputs": truncated,
                         "max_length": model.max_seq_length, "total_ms": (time.perf_counter()-t0)*1000,
                         "model": config["embedding_model"], "revision": config["embedding_revision"],
                         "packages": {n: importlib.metadata.version(n) for n in ["torch", "transformers", "tokenizers", "sentence-transformers"]}})
        print("[SAVED]", path, flush=True)
        partial.unlink(missing_ok=True)
        partial_meta.unlink(missing_ok=True)


def lock_run(run: Path, destination: Path) -> None:
    manifest = json.loads((run / "manifest.json").read_text())
    if manifest["split"] != "dev" or manifest["smoke"]:
        raise ValueError("Lock must come from a full dev run")
    rows = read_jsonl(run / "rankings.jsonl")
    expected = set(manifest["query_ids"])
    chosen = []
    for mode in manifest["configs"]:
        items = [r for r in rows if r["config"] == mode]
        if {r["query_id"] for r in items} != expected or any(r["status"] != "ok" for r in items):
            raise ValueError("Cannot lock an incomplete/failed dev run")
        scores = [r["metrics"][f"ndcg@{manifest['config']['final_k']}"] for r in items if r["answerable"]]
        chosen.append((sum(scores) / len(scores), mode))
    winner = sorted(chosen, key=lambda pair: (-pair[0], pair[1]))[0][1]
    payload = {"config": manifest["config"], "dataset_hash": manifest["dataset_hash"],
               "selection": {"metric": f"ndcg@{manifest['config']['final_k']}", "winner": winner,
                             "dev_run": str(run), "dev_scores": chosen},
               "locked_at": datetime.now(timezone.utc).isoformat(),
               "latency_budget": "quality-first CPU research profile; production p95 target not established",
               "annotation_status": manifest["dataset"]["annotation_status"]}
    payload["source_hashes"] = manifest["source_hashes"]
    payload["configs"] = manifest["configs"]
    payload["lock_hash"] = fingerprint(payload)
    dump(destination, payload)
    print("[LOCKED]", destination, "winner=", winner)


def run(config: dict, args: argparse.Namespace, dataset: dict) -> Path:
    import numpy as np
    from rank_bm25 import BM25Okapi
    from app.bm25_index import tokenize
    chunks = read_jsonl(DATASET / "chunks.jsonl")
    all_queries = read_jsonl(DATASET / f"queries_{args.split}.jsonl")
    light_ids = {q["id"] for q in read_jsonl(SERVICE / "eval/eval_set_light.jsonl")}
    queries = [q for q in all_queries if q["query_id"] in light_ids] if args.smoke else all_queries
    vector_indices = {q["query_id"]: i for i, q in enumerate(all_queries)}
    modes = args.configs.split(",")
    if any(m not in MODES for m in modes) or len(set(modes)) != len(modes):
        raise ValueError("Choose distinct configs from A,B,C,D,E")
    if not 0 < config["final_k"] <= config["candidate_k"] or not 0 <= config["bm25_weight"] <= 1:
        raise ValueError("Invalid retrieval budget or weights")
    if config.get("expansion"):
        raise ValueError("This controlled benchmark requires expansion=false")
    qrels = read_jsonl(DATASET / "qrels.jsonl")
    grades, groups = defaultdict(dict), defaultdict(lambda: defaultdict(list))
    for rel in qrels:
        grades[rel["query_id"]][rel["chunk_id"]] = rel["relevance"]
        groups[rel["query_id"]][rel["chunk_id"]].append(rel["evidence_group_id"])
    need_dense = any(MODES[m][0] != "bm25" for m in modes)
    directory = cache_dir(config, dataset)
    coll = None
    if need_dense:
        import chromadb
        from chromadb.config import Settings
        vectors = np.load(directory / "corpus.npy")
        qvectors = np.load(directory / f"{args.split}.npy")
        for kind, entries, field in [("corpus", chunks, "text"), (args.split, all_queries, "question")]:
            meta = json.loads((directory / f"{kind}.json").read_text())
            if meta["text_hash"] != fingerprint([e[field] for e in entries]):
                raise ValueError("Embedding cache belongs to different texts")
        client = chromadb.PersistentClient(path=str(directory / "chroma"), settings=Settings(anonymized_telemetry=False))
        coll = client.get_or_create_collection("retrieval_v1", metadata={"hnsw:space": "cosine", "hnsw:num_threads": config["threads"]})
        if coll.count() not in {0, len(chunks)}:
            raise ValueError("Partial index; rebuild the isolated benchmark index")
        if not coll.count():
            coll.add(ids=[c["id"] for c in chunks], documents=[c["text"] for c in chunks],
                     metadatas=[c["meta"] for c in chunks], embeddings=vectors.tolist())
    sparse = BM25Okapi([tokenize(c["text"]) for c in chunks])
    by_id = {c["id"]: c for c in chunks}
    reranker = get_reranker(RerankerConfig(model=config["rerank_model"], revision=config["rerank_revision"],
                           device=config["device"], batch_size=config["batch_size"], max_length=config["max_length"],
                           quantize_int8=config.get("quantize_int8", False)))
    os.environ["TORCH_NUM_THREADS"] = str(config["threads"])
    if any(MODES[m][1] for m in modes):
        print("[LOAD] reranker", config["rerank_model"], flush=True)
        reranker.rerank("warmup", [{**chunks[0], "score": 0.0}])
    identity = fingerprint({"config": config, "dataset": dataset, "split": args.split,
                            "modes": modes, "smoke": args.smoke, "repetitions": args.repetitions})[:12]
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output = OUT / f"{args.split}_{config['profile']}_{stamp}_{identity}"
    output.mkdir(parents=True, exist_ok=False)
    packages = {}
    for name in ["torch", "sentence-transformers", "transformers", "numpy", "rank-bm25", "chromadb"]:
        try:
            packages[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            pass
    manifest = {"run_id": output.name, "split": args.split, "smoke": args.smoke,
                "config": config, "configs": modes, "dataset": dataset,
                "dataset_hash": fingerprint(dataset), "started_at": datetime.now(timezone.utc).isoformat(),
                "query_ids": [q["query_id"] for q in queries], "repetitions": args.repetitions,
                "code_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
                "working_tree_diff_sha256": digest(subprocess.check_output(["git", "diff"], cwd=ROOT)),
                "python": platform.python_version(), "platform": platform.platform(), "packages": packages,
                "hardware": {"cpu": platform.processor(), "logical_cpus": os.cpu_count()},
                "measurement": "warm Chroma/BM25/rerank with cached query embeddings; no generation/expansion/API",
                "reranker_model_load_ms": reranker.load_ms,
                "command": sys.argv}
    if need_dense:
        manifest["embedding_cache_metadata"] = {kind: json.loads((directory / f"{kind}.json").read_text())
                                                 for kind in ["corpus", args.split]}
    manifest["source_hashes"] = source_hashes()
    dump(output / "manifest.json", manifest)
    k = config["candidate_k"]
    errors, records, timing_rows, pools = [], [], [], []
    # No silent fail-open: each exception becomes an error row, remains in coverage counts.
    for qi, query in enumerate(queries):
        qid = query["query_id"]
        pool_cache: dict[str, list[dict]] = {}
        try:
            ts = time.perf_counter()
            scores = sparse.get_scores(tokenize(query["question"]))
            indices = sorted(range(len(chunks)), key=lambda i: (-scores[i], chunks[i]["id"]))
            bm = [{**chunks[i], "score": float(scores[i]), "score_type": "bm25"}
                  for i in indices if scores[i] > 0][:k]
            sparse_ms = (time.perf_counter() - ts) * 1000
            dense_ms = 0.0
            de = []
            if need_dense:
                ts = time.perf_counter()
                result = coll.query(query_embeddings=[qvectors[vector_indices[qid]].tolist()], n_results=min(k, len(chunks)), include=["distances"])
                de = [{**by_id[cid], "score": 1.0-float(distance), "score_type": "cosine"}
                      for cid, distance in zip(result["ids"][0], result["distances"][0])]
                dense_ms = (time.perf_counter() - ts) * 1000
            ts = time.perf_counter()
            hy = rrf_fuse(de, bm, k=config["rrf_k"], dense_weight=1-config["bm25_weight"], sparse_weight=config["bm25_weight"])[:k]
            fusion_ms = (time.perf_counter() - ts) * 1000
            pool_cache.update(dense=de, bm25=bm, hybrid=hy)
            ordered_modes = modes[:]
            random.Random(config["seed"] + qi).shuffle(ordered_modes)
            for mode in ordered_modes:
                kind, use_ce = MODES[mode]
                pool = pool_cache[kind]
                pool_hash = candidate_hash(pool)
                ranked = pool
                extra = {"rerank_ms": 0.0, "pairs": 0, "truncated_pairs": 0}
                try:
                    if use_ce:
                        ranked, extra = reranker.rerank(query["question"], pool)
                    metrics = retrieval_metrics([h["id"] for h in ranked], grades[qid], k=config["final_k"],
                                                answerable=query["answerable"], groups=groups[qid],
                                                required_groups=query["required_evidence_groups"])
                    metrics.update(candidate_metrics([h["id"] for h in pool], grades[qid], query["answerable"]))
                    row = {"query_id": qid, "config": mode, "category": query["category"],
                           "intent_group": query["intent_group"], "answerable": query["answerable"],
                           "status": "ok", "candidate_hash": pool_hash, "candidate_count": len(pool),
                           "metrics": metrics, "ranking": [{key: h.get(key) for key in ["id", "score", "score_type", "retrieval_score", "retrieval_rank", "rerank_score", "rerank_rank"]} for h in ranked],
                           "timing": {"dense_search_ms": dense_ms if kind != "bm25" else 0.0,
                                      "bm25_ms": sparse_ms if kind != "dense" else 0.0,
                                      "fusion_ms": fusion_ms if kind == "hybrid" else 0.0, **extra},
                           "known_unjudged_top5": sum(h["id"] not in grades[qid] for h in ranked[:5])}
                    row["timing"]["total_ranking_ms"] = sum(row["timing"][n] for n in ["dense_search_ms", "bm25_ms", "fusion_ms", "rerank_ms"])
                    records.append(row)
                    pools.append({"query_id": qid, "config": mode, "hash": pool_hash,
                                  "hits": [{"id": h["id"], "score": h["score"]} for h in pool]})
                    timing_rows.append({"query_id": qid, "config": mode, "repetition": 0, **row["timing"]})
                    # Subsequent repetitions measure the same candidate pool; never inflate sample size of quality metrics.
                    for repeat in range(1, args.repetitions):
                        if use_ce:
                            _, timing = reranker.rerank(query["question"], pool)
                            timing_rows.append({"query_id": qid, "config": mode, "repetition": repeat,
                                                "rerank_ms": timing["rerank_ms"], "measurement": "rerank_only_replay"})
                except Exception as exc:
                    errors.append({"query_id": qid, "config": mode, "error_type": type(exc).__name__, "error": str(exc)})
                    records.append({"query_id": qid, "config": mode, "answerable": query["answerable"], "status": "error"})
        except Exception as exc:
            for mode in modes:
                errors.append({"query_id": qid, "config": mode, "error_type": type(exc).__name__, "error": str(exc)})
                records.append({"query_id": qid, "config": mode, "answerable": query["answerable"], "status": "error"})
        # Persist after every question. Interrupted runs can still be inspected; no checkpoint mixing.
        write_jsonl(output / "rankings.jsonl", records)
        write_jsonl(output / "candidates.jsonl", pools)
        write_jsonl(output / "errors.jsonl", errors)
        write_jsonl(output / "latency.jsonl", timing_rows)
        print(f"[RANK] {qi+1}/{len(queries)} {qid} errors={len(errors)} -> {output.name}", flush=True)
    manifest.update(finished_at=datetime.now(timezone.utc).isoformat(), errors=len(errors),
                    peak_process_rss_mb=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024)
    dump(output / "manifest.json", manifest)
    print("[RESULT]", output, flush=True)
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=CONFIG)
    parser.add_argument("--split", choices=["dev", "test"], default="dev")
    parser.add_argument("--configs", default="A,B,C,D,E")
    parser.add_argument("--stage", choices=["embed", "rank"], default="rank")
    parser.add_argument("--smoke", action="store_true")
    parser.add_argument("--repetitions", type=int, default=1)
    parser.add_argument("--validate-data", action="store_true")
    parser.add_argument("--lock-from", type=Path)
    parser.add_argument("--locked-config", type=Path)
    args = parser.parse_args()
    if args.repetitions < 1:
        parser.error("repetitions must be positive")
    if args.smoke and args.split != "dev":
        parser.error("--smoke is only supported on dev; test requires the full locked protocol")
    dataset = validate()
    if args.validate_data:
        print(json.dumps(dataset, ensure_ascii=False, indent=2))
        return
    if args.lock_from:
        lock_run(args.lock_from, OUT / "locked_config.json")
        return
    config = json.loads(args.config.read_text())
    if args.split == "test":
        if not args.locked_config:
            parser.error("test requires --locked-config created from a complete dev run")
        locked = json.loads(args.locked_config.read_text())
        expected = locked.pop("lock_hash")
        if fingerprint(locked) != expected or locked["dataset_hash"] != fingerprint(dataset):
            raise ValueError("Lock/dataset hash mismatch")
        if locked["source_hashes"] != source_hashes():
            raise ValueError("Benchmark source changed after dev lock; rerun dev before test")
        if not set(args.configs.split(",")) <= set(locked["configs"]):
            raise ValueError("Test configs must have been evaluated on dev")
        config = locked["config"]
    os.environ["TOKENIZERS_PARALLELISM"] = "false"
    if args.stage == "embed":
        embed(config, args.split, dataset)
    else:
        output = run(config, args, dataset)
        if json.loads((output / "manifest.json").read_text())["errors"]:
            raise SystemExit(2)


if __name__ == "__main__":
    main()
