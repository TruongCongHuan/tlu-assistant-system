"""Compare RRF weights on identical recorded dense/BM25 pools, without ANN noise."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SERVICE = ROOT / "services/rag-api"
sys.path.insert(0, str(SERVICE))
from app.retrieval import candidate_hash, rrf_fuse
from eval.build_retrieval_dataset import DATASET, digest, read_jsonl, validate, write_jsonl
from eval.retrieval_metrics import retrieval_metrics, candidate_metrics
from eval.report_retrieval_benchmark import cluster_ci, write_csv
from eval.run_retrieval_benchmark import dump, fingerprint, source_hashes


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reference-run", required=True, type=Path)
    parser.add_argument("--weight", type=float, default=.5)
    args = parser.parse_args()
    if not 0 <= args.weight <= 1:
        parser.error("weight must be in [0, 1]")
    parent = json.loads((args.reference_run / "manifest.json").read_text())
    dataset = validate()
    if parent["dataset_hash"] != fingerprint(dataset) or parent["source_hashes"] != source_hashes():
        raise ValueError("Reference dataset/code changed")
    config = parent["config"]
    chunks = {c["id"]: c for c in read_jsonl(DATASET / "chunks.jsonl")}
    queries = {q["query_id"]: q for q in read_jsonl(DATASET / f"queries_{parent['split']}.jsonl")}
    pools = {(r["query_id"], r["config"]): r for r in read_jsonl(args.reference_run / "candidates.jsonl")}
    originals = {(r["query_id"], r["config"]): r for r in read_jsonl(args.reference_run / "rankings.jsonl") if r["status"] == "ok"}
    qrels = read_jsonl(DATASET / "qrels.jsonl")
    records = []
    for qid in parent["query_ids"]:
        query = queries[qid]
        def hits(mode):
            return [{**chunks[h["id"]], "score": h["score"]} for h in pools[(qid, mode)]["hits"]]
        dense, sparse = hits("A"), hits("B")
        def fuse(weight):
            return rrf_fuse(dense, sparse, k=config["rrf_k"], dense_weight=1-weight,
                            sparse_weight=weight)[:config["candidate_k"]]
        original = fuse(config["bm25_weight"])
        if candidate_hash(original) != pools[(qid, "C")]["hash"]:
            raise ValueError(f"Cannot reproduce parent fusion: {qid}")
        ranked = fuse(args.weight)
        rels = [r for r in qrels if r["query_id"] == qid]
        grades = {r["chunk_id"]: r["relevance"] for r in rels}
        groups = {}
        for rel in rels:
            groups.setdefault(rel["chunk_id"], []).append(rel["evidence_group_id"])
        ids = [h["id"] for h in ranked]
        metrics = retrieval_metrics(ids, grades, k=config["final_k"], answerable=query["answerable"],
                                    groups=groups, required_groups=query["required_evidence_groups"])
        metrics.update(candidate_metrics(ids, grades, query["answerable"]))
        records.append({"query_id": qid, "intent_group": query["intent_group"], "category": query["category"],
                        "answerable": query["answerable"], "status": "ok", "config": f"C_w{args.weight}",
                        "metrics": metrics, "candidate_hash": candidate_hash(ranked),
                        "ranking": [{"id": h["id"], "score": h["score"]} for h in ranked]})
    answerable = [r for r in records if r["answerable"]]
    metrics = {key: sum(r["metrics"][key] for r in answerable)/len(answerable)
               for key in answerable[0]["metrics"] if all(r["metrics"][key] is not None for r in answerable)}
    paired = {}
    new = {r["query_id"]: r for r in answerable}
    for mode in ["A", "C"]:
        baseline = {qid: r for (qid, c), r in originals.items() if c == mode and r["answerable"]}
        paired[f"replay-{mode}"] = {"ndcg": cluster_ci(baseline, new, f"ndcg@{config['final_k']}"),
                                      "mrr": cluster_ci(baseline, new, f"mrr@{config['final_k']}")}
    output = ROOT / "docs/benchmarks" / f"fusion_replay_{parent['run_id']}_w{args.weight}"
    output.mkdir(parents=True, exist_ok=True)
    write_jsonl(output / "rankings.jsonl", records)
    write_csv(output / "per_query.csv", [{"query_id": r["query_id"], "answerable": r["answerable"], **r["metrics"]} for r in records])
    dump(output / "summary.json", {"n": len(records), "n_answerable": len(answerable), "metrics": metrics})
    dump(output / "comparison.json", paired)
    dump(output / "manifest.json", {"reference_run": str(args.reference_run), "weight": args.weight,
                                    "reference_weight": config["bm25_weight"], "dataset_hash": fingerprint(dataset),
                                    "source_hashes": source_hashes(), "script_sha256": digest(Path(__file__).read_bytes()),
                                    "reference_candidate_file_sha256": digest((args.reference_run / "candidates.jsonl").read_bytes()),
                                    "measurement": "offline fusion-quality replay on identical recorded pools; no live retrieval latency",
                                    "exploratory": True, "parent_fusion_verified_queries": len(records)})
    print("[FUSION REPLAY]", output)
    print(json.dumps(metrics, ensure_ascii=False))


if __name__ == "__main__":
    main()
