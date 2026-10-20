"""Inspect real ranked evidence and whether reranker token truncation hid its span."""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SERVICE = ROOT / "services/rag-api"
sys.path.insert(0, str(SERVICE))
from eval.build_retrieval_dataset import DATASET, digest, read_jsonl, validate
from eval.run_retrieval_benchmark import dump, fingerprint


def normalized_offsets(text: str) -> tuple[str, list[int]]:
    chars, positions = [], []
    for match in re.finditer(r"\S+", text):
        if chars:
            chars.append(" ")
            positions.append(match.start())
        for pos in range(match.start(), match.end()):
            chars.append(text[pos])
            positions.append(pos)
    return "".join(chars), positions


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True)
    args = parser.parse_args()
    dataset = validate()
    manifest = json.loads((args.run_dir / "manifest.json").read_text())
    if fingerprint(dataset) != manifest["dataset_hash"]:
        raise ValueError("Dataset changed since run")
    from transformers import AutoTokenizer
    config = manifest["config"]
    tokenizer = AutoTokenizer.from_pretrained(config["rerank_model"], revision=config["rerank_revision"],
                                             trust_remote_code=False, local_files_only=True)
    if not tokenizer.is_fast:
        raise ValueError("Offset analysis requires the model's fast tokenizer")
    queries = {q["query_id"]: q for q in read_jsonl(DATASET / f"queries_{manifest['split']}.jsonl")}
    chunks = {c["id"]: c for c in read_jsonl(DATASET / "chunks.jsonl")}
    rels = read_jsonl(DATASET / "qrels.jsonl")
    rows = {(r["query_id"], r["config"]): r for r in read_jsonl(args.run_dir / "rankings.jsonl") if r["status"] == "ok"}
    cases = []
    for qid, query in queries.items():
        if not query["answerable"]:
            continue
        relevant = [r for r in rels if r["query_id"] == qid and r["relevance"] >= 2]
        gold = {r["chunk_id"] for r in relevant}
        ranks = {}
        for mode in manifest["configs"]:
            row = rows.get((qid, mode))
            ranks[mode] = next((i for i, h in enumerate(row["ranking"], 1) if h["id"] in gold), None) if row else None
        evidence = []
        for cid in sorted(gold):
            text = chunks[cid]["text"]
            full = tokenizer(query["question"], text, truncation=False, verbose=False)
            encoded = tokenizer(query["question"], text, truncation=True, max_length=config["max_length"],
                                return_offsets_mapping=True, verbose=False)
            visible_end = max((end for (start, end), seq in zip(encoded["offset_mapping"], encoded.sequence_ids()) if seq == 1), default=0)
            normalized, offsets = normalized_offsets(text)
            spans = []
            for rel in relevant:
                if rel["chunk_id"] != cid:
                    continue
                quote = re.sub(r"\s+", " ", rel["source_span"]).strip()
                position = normalized.find(quote)
                if position < 0:
                    raise ValueError(f"Gold quote missing from recorded chunk: {qid}/{cid}")
                start, end = offsets[position], offsets[position+len(quote)-1]+1
                spans.append({"source_quote": rel["source_span"], "start_char": start, "end_char": end,
                              "fully_visible": end <= visible_end, "partly_visible": start < visible_end < end})
            evidence.append({"chunk_id": cid, "heading": chunks[cid]["meta"]["heading_path"],
                             "full_pair_tokens": len(full["input_ids"]), "visible_document_end_char": visible_end,
                             "truncated": len(full["input_ids"]) > config["max_length"], "spans": spans})
        cases.append({"query_id": qid, "question": query["question"], "category": query["category"],
                      "first_gold_ranks": ranks, "gold_evidence": evidence})
    output = ROOT / "docs/benchmarks" / args.run_dir.name
    output.mkdir(parents=True, exist_ok=True)
    dump(output / "case_review.json", {"run_id": args.run_dir.name, "max_length": config["max_length"],
                                      "script_sha256": digest(Path(__file__).read_bytes()), "cases": cases,
                                      "caution": "A missing span is an observed input limitation; attribution requires a controlled counterfactual. Gold annotations remain incomplete and pending human review."})
    print("[CASES]", output / "case_review.json")


if __name__ == "__main__":
    main()
