"""Meaningful metric, ranking and service integration regression checks."""
from __future__ import annotations

import math
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

SERVICE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SERVICE))
from app.chunking import chunk_text_fixed, chunk_text_semantic
from app.retrieval import candidate_hash, deduplicate_best, rrf_fuse
from app.reranker import CrossEncoderReranker, RerankerConfig
from eval.retrieval_metrics import candidate_metrics, retrieval_metrics
from eval.build_retrieval_dataset import DATASET, read_jsonl, validate
from eval.error_analysis import classify_row


def hit(cid, score, text=None):
    return {"id": cid, "text": text or cid, "score": score, "meta": {"doc_name": "test.md"}}


class MetricsTests(unittest.TestCase):
    def test_rank_three_and_miss_have_explicit_cutoff(self):
        gold = {"correct": 2}
        self.assertEqual(retrieval_metrics(["a", "b", "correct"], gold, k=5)["mrr@5"], 1/3)
        self.assertEqual(retrieval_metrics(["a", "b", "correct"], gold, k=2)["mrr@2"], 0)
        self.assertEqual(retrieval_metrics([], gold)["hit@5"], 0)

    def test_multiple_relevant_never_inflate_ndcg(self):
        gold = {"a": 2, "b": 2}
        m = retrieval_metrics(["a", "b"], gold, k=5)
        self.assertEqual(m["ndcg@5"], 1)
        self.assertEqual(m["precision@5"], .4)
        self.assertEqual(m["recall@5"], 1)

    def test_graded_gain_and_evidence_groups(self):
        gold = {"partial": 1, "yes": 2, "other": 2}
        m = retrieval_metrics(["partial", "yes"], gold, k=3,
                              groups={"yes": ["E1"], "other": ["E2"]}, required_groups=["E1", "E2"])
        dcg = 1 + 3/math.log2(3)
        idcg = 3 + 3/math.log2(3) + 1/math.log2(4)
        self.assertAlmostEqual(m["ndcg@3"], dcg/idcg)
        self.assertEqual(m["mrr@3"], .5)
        self.assertEqual(m["evidence_coverage"], .5)
        self.assertEqual(m["all_evidence"], 0)

    def test_duplicates_do_not_earn_double_gain(self):
        self.assertEqual(retrieval_metrics(["a", "a"], {"a": 2})["precision@5"], .2)

    def test_oos_is_null_not_zero(self):
        self.assertTrue(all(v is None for v in retrieval_metrics(["x"], {}, answerable=False).values()))
        self.assertIsNone(candidate_metrics([], {}, False)["candidate_recall"])

    def test_missing_gold_and_invalid_budget_rejected(self):
        with self.assertRaises(ValueError):
            retrieval_metrics([], {})
        with self.assertRaises(ValueError):
            retrieval_metrics([], {"a": 2}, k=0)


class RankingTests(unittest.TestCase):
    def test_dedup_keeps_best_variant_and_stable_ties(self):
        hits = deduplicate_best([hit("b", 1), hit("a", 1), hit("a", 3)])
        self.assertEqual([h["id"] for h in hits], ["a", "b"])
        self.assertEqual(hits[0]["score"], 3)

    def test_rrf_combines_ranks_without_summing_raw_scores(self):
        ranked = rrf_fuse([hit("a", .9), hit("b", .8)], [hit("b", 100), hit("c", 50)], dense_weight=.5, sparse_weight=.5)
        self.assertEqual(ranked[0]["id"], "b")
        self.assertAlmostEqual(ranked[0]["score"], .5/62+.5/61)

    def test_hash_detects_text_order_and_score_changes(self):
        a, b = hit("a", 1), hit("b", 2)
        self.assertNotEqual(candidate_hash([a, b]), candidate_hash([b, a]))
        self.assertNotEqual(candidate_hash([a]), candidate_hash([hit("a", 2)]))

    def test_reranking_preserves_metadata_and_pool(self):
        import numpy as np
        class FakeModel:
            def tokenizer(self, pairs, **kwargs):
                return {"input_ids": [[1]*10 for _ in pairs]}
            def predict(self, pairs, **kwargs):
                return np.array([.1, .9])
        ranker = CrossEncoderReranker(RerankerConfig())
        ranker._model = FakeModel()
        candidates = [hit("a", .9), hit("b", .5)]
        ranked, info = ranker.rerank("query", candidates)
        self.assertEqual([h["id"] for h in ranked], ["b", "a"])
        self.assertEqual(ranked[0]["retrieval_rank"], 2)
        self.assertEqual(ranked[0]["retrieval_score"], .5)
        self.assertEqual(candidates[0]["score"], .9)
        self.assertEqual(info["pairs"], 2)
        self.assertEqual(ranker.rerank("x", [])[0], [])

    def test_chunking_is_deterministic_and_overlap_is_validated(self):
        text = "## Title\n" + "A useful paragraph of evidence. "*50
        self.assertEqual(chunk_text_semantic(text, "doc", "x.md"), chunk_text_semantic(text, "doc", "x.md"))
        with self.assertRaises(ValueError):
            chunk_text_fixed(text, "doc", "x.md", 20, 20)

    def test_false_refusal_was_not_inverted(self):
        common = {"category": "direct", "hit_rate_at_k": "1", "faithfulness": "1", "context_precision": "1"}
        self.assertNotIn("false_refusal", classify_row({**common, "refusal_correct": "1"}))
        self.assertIn("false_refusal", classify_row({**common, "refusal_correct": "0"}))


class DatasetTests(unittest.TestCase):
    def test_hashes_and_disjoint_evidence(self):
        manifest = validate()
        self.assertEqual(manifest["queries"], {"dev": 50, "test": 100})
        self.assertEqual(manifest["shared_positive_chunks_between_splits"], [])
        self.assertFalse(manifest["qrels_complete"])
        qrels = read_jsonl(DATASET / "qrels.jsonl")
        graded = {r["query_id"] for r in qrels}
        for split in ["dev", "test"]:
            for q in read_jsonl(DATASET / f"queries_{split}.jsonl"):
                self.assertEqual(q["query_id"] in graded, q["answerable"])

    def test_cluster_bootstrap_uses_paired_queries(self):
        from eval.report_retrieval_benchmark import cluster_ci
        a = {"q1": {"metrics": {"ndcg@5": .2}, "intent_group": "same"},
             "q2": {"metrics": {"ndcg@5": .3}, "intent_group": "same"}}
        b = {"q1": {"metrics": {"ndcg@5": .7}, "intent_group": "same"},
             "q2": {"metrics": {"ndcg@5": .8}, "intent_group": "same"}}
        result = cluster_ci(a, b, "ndcg@5")
        self.assertEqual(result["n"], 2)
        self.assertEqual(result["intent_groups"], 1)
        self.assertAlmostEqual(result["mean_delta"], .5)
        self.assertAlmostEqual(result["ci_low"], .5)
        self.assertAlmostEqual(result["ci_high"], .5)

    def test_test_split_requires_a_lock(self):
        import subprocess
        result = subprocess.run([sys.executable, str(SERVICE / "eval/run_retrieval_benchmark.py"), "--split", "test"],
                                capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("requires --locked-config", result.stderr)


class ServiceIntegrationTests(unittest.TestCase):
    def test_sparse_mode_does_not_call_embedding_or_expansion(self):
        from app import rag
        with patch.multiple(rag, RETRIEVAL_MODE="bm25", RERANK_MODE="none", CANDIDATE_K=20, FINAL_K=5), \
             patch.object(rag, "expand_query", side_effect=AssertionError("expansion called")), \
             patch.object(rag, "_embed_via_rest", side_effect=AssertionError("embedding called")), \
             patch.object(rag.bm25_index, "search", return_value=[hit("a", 2)]):
            context, sources, chunks = rag.retrieve_context("query", None)
        self.assertIn("a", context)
        self.assertEqual(sources, "test.md")
        self.assertEqual(chunks[0]["retrieval_info"]["candidate_count"], 1)

    def test_rerank_happens_before_final_cut(self):
        from app import rag
        from app import reranker
        from types import SimpleNamespace
        hits = [hit(str(i), 20-i) for i in range(20)]
        def reverse(question, pool):
            self.assertEqual(len(pool), 20)
            return list(reversed(pool)), {"rerank_ms": 1}
        with patch.multiple(rag, RETRIEVAL_MODE="bm25", RERANK_MODE="cross_encoder", CANDIDATE_K=20, FINAL_K=5), \
             patch.object(rag.bm25_index, "search", return_value=hits), \
             patch.object(reranker, "get_reranker", return_value=SimpleNamespace(rerank=reverse)):
            _, _, chunks = rag.retrieve_context("query", None)
        self.assertEqual(len(chunks), 5)
        self.assertEqual(chunks[0]["id"], "19")

    def test_legacy_eval_excludes_oos_and_uses_matching_gold(self):
        from eval import run_eval
        oos = run_eval.compute_retrieval_metrics([], "N/A", 5, query_id="Q23")
        self.assertTrue(all(v is None for v in oos.values()))
        rel = next(r for r in read_jsonl(DATASET / "qrels.jsonl") if r["query_id"] == "Q05")
        chunk = next(c for c in read_jsonl(DATASET / "chunks.jsonl") if c["id"] == rel["chunk_id"])
        metrics = run_eval.compute_retrieval_metrics([chunk], "unused", 5, query_id="Q05")
        self.assertEqual(metrics["hit_rate_at_k"], 1)
        self.assertLessEqual(metrics["ndcg"], 1)


if __name__ == "__main__":
    unittest.main()
