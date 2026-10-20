"""Export reproducible tables, paired cluster bootstrap and plots from real runs."""
from __future__ import annotations

import argparse
import csv
import json
import random
import shutil
import statistics
import sys
from collections import defaultdict
from pathlib import Path

SERVICE = Path(__file__).resolve().parents[1]
ROOT = SERVICE.parents[1]
sys.path.insert(0, str(SERVICE))
from eval.build_retrieval_dataset import DATASET, read_jsonl
from eval.run_retrieval_benchmark import dump


def percentile(values: list[float], p: float) -> float | None:
    if not values:
        return None
    values = sorted(values)
    pos = (len(values)-1)*p
    low = int(pos)
    high = min(low+1, len(values)-1)
    return values[low] + (values[high]-values[low])*(pos-low)


def cluster_ci(rows_a: dict, rows_b: dict, field: str, seed: int = 42) -> dict:
    ids = sorted(set(rows_a) & set(rows_b))
    clusters = defaultdict(list)
    diffs = []
    for qid in ids:
        a, b = rows_a[qid], rows_b[qid]
        av, bv = a["metrics"].get(field), b["metrics"].get(field)
        if av is None or bv is None:
            continue
        diff = bv-av
        diffs.append(diff)
        clusters[a["intent_group"]].append(diff)
    if not diffs:
        return {"n": 0}
    values = list(clusters.values())
    rng = random.Random(seed)
    means = []
    for _ in range(2000):
        sampled = [d for _ in values for d in rng.choice(values)]
        means.append(statistics.mean(sampled))
    return {"n": len(diffs), "intent_groups": len(clusters), "mean_delta": statistics.mean(diffs),
            "ci_low": percentile(means, .025), "ci_high": percentile(means, .975),
            "method": "paired intent-group percentile bootstrap", "resamples": 2000, "seed": seed}


def write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        path.write_text("")
        return
    fields = sorted(set().union(*(r.keys() for r in rows)))
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fields)
        writer.writeheader()
        writer.writerows(rows)


def generate(run_dir: Path) -> dict:
    manifest = json.loads((run_dir / "manifest.json").read_text())
    rows = read_jsonl(run_dir / "rankings.jsonl")
    if len({(r["config"], r["query_id"]) for r in rows}) != len(rows):
        raise ValueError("Duplicate (config, query_id) records")
    expected = set(manifest["query_ids"])
    summaries = {}
    k = manifest["config"]["final_k"]
    for config in manifest["configs"]:
        items = [r for r in rows if r["config"] == config]
        ok = [r for r in items if r["status"] == "ok"]
        inscope = [r for r in ok if r["answerable"]]
        metric_names = sorted(set().union(*(r["metrics"] for r in inscope))) if inscope else []
        summary = {"n_expected": len(expected), "n_records": len(items), "n_ok": len(ok),
                   "n_answerable_ok": len(inscope), "n_oos_ok": len(ok)-len(inscope),
                   "missing_ids": sorted(expected-set(r["query_id"] for r in items)),
                   "errors": len(items)-len(ok)}
        summary["metrics"] = {name: statistics.mean(r["metrics"][name] for r in inscope if r["metrics"].get(name) is not None)
                              for name in metric_names
                              if any(r["metrics"].get(name) is not None for r in inscope)}
        summary["timing"] = {}
        for name in ["dense_search_ms", "bm25_ms", "fusion_ms", "rerank_ms", "total_ranking_ms"]:
            values = [r["timing"][name] for r in ok]
            summary["timing"][name] = {"mean": statistics.mean(values) if values else None,
                                      "p50": percentile(values, .5), "p95": percentile(values, .95)}
        summary["truncated_pairs"] = sum(r["timing"].get("truncated_pairs", 0) for r in ok)
        summary["rerank_pairs"] = sum(r["timing"].get("pairs", 0) for r in ok)
        summary["unjudged_top5"] = sum(r["known_unjudged_top5"] for r in inscope)
        summary["by_category"] = {}
        for category in sorted({r["category"] for r in inscope}):
            subset = [r for r in inscope if r["category"] == category]
            summary["by_category"][category] = {"n": len(subset), f"ndcg@{k}": statistics.mean(r["metrics"][f"ndcg@{k}"] for r in subset),
                                                f"hit@{k}": statistics.mean(r["metrics"][f"hit@{k}"] for r in subset)}
        summaries[config] = summary
    comparisons = {}
    for a, b in [("A", "D"), ("C", "E"), ("A", "C")]:
        if a not in summaries or b not in summaries:
            continue
        ra = {r["query_id"]: r for r in rows if r["config"] == a and r["status"] == "ok" and r["answerable"]}
        rb = {r["query_id"]: r for r in rows if r["config"] == b and r["status"] == "ok" and r["answerable"]}
        common = set(ra) & set(rb)
        if b in {"D", "E"} and any(ra[q]["candidate_hash"] != rb[q]["candidate_hash"] for q in common):
            raise ValueError("Rerank and baseline candidate pools differ")
        gained = [q for q in sorted(common) if rb[q]["metrics"][f"hit@{k}"] > ra[q]["metrics"][f"hit@{k}"]]
        lost = [q for q in sorted(common) if rb[q]["metrics"][f"hit@{k}"] < ra[q]["metrics"][f"hit@{k}"]]
        discord = len(gained)+len(lost)
        if discord:
            import math
            pvalue = min(1.0, 2*sum(math.comb(discord, i) for i in range(min(len(gained), len(lost))+1))/(2**discord))
        else:
            pvalue = 1.0
        comparisons[f"{b}-{a}"] = {"n_paired": len(common), "gained_hit": gained, "lost_hit": lost,
                                    "mcnemar_exact_p": pvalue,
                                    "caution": "McNemar treats queries independently; cluster bootstrap below handles shared intent groups",
                                    "ndcg": cluster_ci(ra, rb, f"ndcg@{k}"),
                                    "mrr": cluster_ci(ra, rb, f"mrr@{k}")}
    summary = {"run_id": run_dir.name, "annotation_status": manifest["dataset"]["annotation_status"],
               "qrels_complete": False, "configs": summaries}
    dump(run_dir / "summary.json", summary)
    dump(run_dir / "comparison.json", comparisons)
    flat = [{"query_id": r["query_id"], "config": r["config"], "status": r["status"],
             "answerable": r["answerable"], "category": r.get("category"), "intent_group": r.get("intent_group"),
             **r.get("metrics", {}), **r.get("timing", {})} for r in rows]
    write_csv(run_dir / "per_query.csv", flat)
    write_csv(run_dir / "latency.csv", read_jsonl(run_dir / "latency.jsonl"))
    export = ROOT / "docs/benchmarks" / run_dir.name
    export.mkdir(parents=True, exist_ok=True)
    for name in ["manifest.json", "summary.json", "comparison.json", "per_query.csv", "latency.csv", "errors.jsonl", "rankings.jsonl", "candidates.jsonl"]:
        shutil.copy2(run_dir / name, export / name)
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    labels = list(summaries)
    fig, axes = plt.subplots(1, 2, figsize=(10, 4))
    axes[0].bar(labels, [summaries[c]["metrics"].get(f"ndcg@{k}", 0) for c in labels])
    axes[0].set(ylim=(0, 1), ylabel=f"known-gold nDCG@{k}", title="Retrieval quality (answerable queries)")
    for c in labels:
        x = summaries[c]["timing"]["total_ranking_ms"]["p95"]
        y = summaries[c]["metrics"].get(f"ndcg@{k}", 0)
        if x is not None:
            axes[1].scatter(x, y)
            axes[1].annotate(c, (x, y))
    axes[1].set(xlabel="p95 cached-vector ranking (ms, log scale)", ylabel=f"known-gold nDCG@{k}", ylim=(0, 1), xscale="log")
    fig.tight_layout()
    fig.savefig(export / "quality_latency.png", dpi=160)
    plt.close(fig)
    table = ["| Config | n answerable | Candidate Hit@K | Known-gold Recall@K | Hit@5 | MRR@5 | nDCG@5 | Ranking p50/p95 ms |", "|---|---:|---:|---:|---:|---:|---:|---|"]
    for c, s in summaries.items():
        m, t = s["metrics"], s["timing"]["total_ranking_ms"]
        table.append(f"| {c} | {s['n_answerable_ok']} | {m.get('candidate_hit',0):.4f} | {m.get('candidate_recall',0):.4f} | {m.get('hit@5',0):.4f} | {m.get('mrr@5',0):.4f} | {m.get('ndcg@5',0):.4f} | {t['p50']:.1f} / {t['p95']:.1f} |")
    lines = ["# Báo cáo benchmark retrieval/reranking TLU", "", f"Run: `{run_dir.name}`; split `{manifest['split']}`; smoke={manifest['smoke']}.",
             "", "**Kết quả đo thật trên bộ nhãn thử nghiệm do agent biên soạn và kiểm tra nguồn; chưa được người độc lập thẩm định.**",
             "Không sinh câu trả lời hoặc gọi judge LLM, theo phạm vi người dùng đã chốt.", "",
             f"Corpus có {manifest['dataset']['chunk_count']} chunk; candidate K={manifest['config']['candidate_k']}, final K={k}.",
             f"Embedding: `{manifest['config']['embedding_model']}`; reranker: `{manifest['config']['rerank_model']}`.",
             f"Chế độ int8: {manifest['config'].get('quantize_int8', False)}; peak process RSS={manifest.get('peak_process_rss_mb', 0):.0f} MiB.",
             "Các revision, cấu hình, source hashes và môi trường nằm trong [manifest](manifest.json).", "", *table, "",
             "A = Dense; B = BM25; C = Hybrid RRF; D = Dense + Cross-Encoder; E = Hybrid + Cross-Encoder.",
             "", "## So sánh theo cặp", ""]
    for name, comparison in comparisons.items():
        ci = comparison["ndcg"]
        if ci.get("n"):
            lines.append(f"- {name}: Δ nDCG@{k}={ci['mean_delta']:+.4f}, bootstrap CI 95% [{ci['ci_low']:+.4f}, {ci['ci_high']:+.4f}], {ci['n']} câu/{ci['intent_groups']} nhóm; Hit tăng {len(comparison['gained_hit'])}, giảm {len(comparison['lost_hit'])} câu.")
    lines += ["", "## Giới hạn và cách đọc", "",
              "- Đây là known-gold metrics trên evidence đã chỉ định, chưa phải qrels đầy đủ toàn corpus. Candidate ngoài tập positive chưa được gán nhãn âm; không kết luận mọi kết quả khác là sai.",
              "- OOS bị loại khỏi mẫu số retrieval; không thể suy ra tỷ lệ từ chối vì không chạy generation hoặc bộ phân loại answerability.",
              "- Độ trễ đo Chroma/BM25/rerank với vector query đã cache, chưa gồm embedding query, cold model load hoặc network. Các trường thời gian thành phần không đồng nghĩa latency API live.",
              f"- Lượt lặp cấu hình: {manifest['repetitions']}; nếu chỉ 1 lượt thì p95 chỉ mô tả các câu trong lượt đó, chưa đáp ứng đánh giá độ ổn định vận hành 3 lượt.",
              "- Hai cấu hình có/không rerank dùng cùng hash candidate pool. Các intent cùng nguồn được giữ cùng split và dùng cluster bootstrap.",
              "- Bảng chi tiết gồm coverage và lỗi trong [summary](summary.json); không dùng số mẫu cũ làm baseline.",
              "", "![Chất lượng và độ trễ](quality_latency.png)", "",
              "## Artifacts", "", "[Per query](per_query.csv), [rankings](rankings.jsonl), [candidate pools](candidates.jsonl), [paired comparisons](comparison.json), [latency](latency.csv), [errors](errors.jsonl).", ""]
    # Actual examples: top rank changes, losses and candidate misses; link IDs back to committed qrels/source spans.
    lines += ["## Ví dụ kiểm tra được", "", "| Query | Config | Top-5 chunk IDs | Loại |", "|---|---|---|---|"]
    examples = []
    for r in rows:
        if r["status"] != "ok" or not r["answerable"]:
            continue
        kind = "candidate_miss" if r["metrics"]["candidate_hit"] == 0 else ("top5_miss" if r["metrics"].get(f"hit@{k}") == 0 else "hit")
        if sum(x[0] == kind for x in examples) < 3:
            examples.append((kind, r))
    for kind, r in examples:
        lines.append(f"| {r['query_id']} | {r['config']} | {', '.join(h['id'] for h in r['ranking'][:k])} | {kind} |")
    (export / "report.md").write_text("\n".join(lines) + "\n")
    print("[REPORT]", export / "report.md")
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", required=True, type=Path)
    args = parser.parse_args()
    generate(args.run_dir)
