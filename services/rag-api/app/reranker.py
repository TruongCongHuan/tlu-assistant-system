"""Optional Cross-Encoder inference. Importing this module never loads torch/weights."""
from __future__ import annotations

import math
import os
import threading
import time
from dataclasses import dataclass
from functools import lru_cache
from typing import Any


@dataclass(frozen=True)
class RerankerConfig:
    model: str = "BAAI/bge-reranker-v2-m3"
    revision: str = "953dc6f6f85a1b2dbfca4c34a2796e7dde08d41e"
    device: str = "cpu"
    batch_size: int = 1
    max_length: int = 512
    quantize_int8: bool = False

    def __post_init__(self) -> None:
        if self.batch_size < 1 or self.max_length < 8:
            raise ValueError("batch_size must be positive and max_length >= 8")

    @classmethod
    def from_env(cls) -> RerankerConfig:
        return cls(model=os.getenv("RERANK_MODEL", cls.model),
                   revision=os.getenv("RERANK_REVISION", cls.revision),
                   device=os.getenv("RERANK_DEVICE", "cpu"),
                   batch_size=int(os.getenv("RERANK_BATCH_SIZE", "1")),
                   max_length=int(os.getenv("RERANK_MAX_LENGTH", "512")),
                   quantize_int8=os.getenv("RERANK_INT8", "0") == "1")


class CrossEncoderReranker:
    def __init__(self, config: RerankerConfig):
        self.config = config
        self._model: Any = None
        self._lock = threading.Lock()
        self.load_ms = 0.0

    def load(self) -> Any:
        # Called under the per-instance lock by rerank; loading is intentionally lazy.
        if self._model is None:
            import torch
            from sentence_transformers import CrossEncoder
            torch.set_num_threads(int(os.getenv("TORCH_NUM_THREADS", "2")))
            t0 = time.perf_counter()
            self._model = CrossEncoder(self.config.model, revision=self.config.revision,
                                       device=self.config.device, max_length=self.config.max_length,
                                       trust_remote_code=False)
            if self.config.quantize_int8:
                if self.config.device != "cpu":
                    raise ValueError("Dynamic int8 inference requires device=cpu")
                self._model.model = torch.quantization.quantize_dynamic(
                    self._model.model, {torch.nn.Linear}, dtype=torch.qint8, inplace=True)
            self.load_ms = (time.perf_counter() - t0) * 1000
        return self._model

    def rerank(self, question: str, candidates: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        if not candidates:
            return [], {"rerank_ms": 0.0, "pairs": 0, "truncated_pairs": 0}
        with self._lock:
            model = self.load()
            pairs = [(question, str(c["text"])) for c in candidates]
            t0 = time.perf_counter()
            encoded = model.tokenizer(pairs, truncation=False, padding=False, verbose=False)
            lengths = [len(ids) for ids in encoded["input_ids"]]
            scores = model.predict(pairs, batch_size=self.config.batch_size,
                                   show_progress_bar=False, convert_to_numpy=True)
            scores = scores.reshape(-1).tolist()
            if len(scores) != len(candidates) or any(not math.isfinite(s) for s in scores):
                raise ValueError("Cross-Encoder returned invalid scores")
            ranked = [{**c, "retrieval_score": c["score"], "retrieval_rank": i,
                       "rerank_score": float(score), "score": float(score),
                       "score_type": "cross_encoder"}
                      for i, (c, score) in enumerate(zip(candidates, scores), 1)]
            ranked.sort(key=lambda c: (-c["rerank_score"], str(c["id"])))
            for rank, hit in enumerate(ranked, 1):
                hit["rerank_rank"] = rank
            return ranked, {"rerank_ms": (time.perf_counter() - t0) * 1000,
                            "pairs": len(pairs), "truncated_pairs": sum(n > self.config.max_length for n in lengths),
                            "max_pair_tokens": max(lengths), "model_load_ms": self.load_ms}


@lru_cache(maxsize=2)
def _cached_reranker(config: RerankerConfig) -> CrossEncoderReranker:
    return CrossEncoderReranker(config)


_FACTORY_LOCK = threading.Lock()


def get_reranker(config: RerankerConfig) -> CrossEncoderReranker:
    # lru_cache alone can execute the factory twice on concurrent first requests.
    with _FACTORY_LOCK:
        return _cached_reranker(config)
