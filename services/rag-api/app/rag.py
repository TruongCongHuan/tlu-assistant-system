"""RAG core: Chroma + Gemini embeddings + generation.

Canonical logic ported from Flutter local RAG (lib/services/):
  - pdf_service.dart  → Semantic Markdown Chunking
  - local_rag_service.dart → query expansion, multi-query, dedup, 5-step prompt
  - embedding_service.dart → gemini-embedding-2-preview, batch-8, 120ms delay

Ablation flags (set via environment variables):
  CHUNK_MODE      = "semantic" (default) | "fixed"
  EXPAND_ON       = "1" (default) | "0"
  TOP_K           = "8" (default, effective context window is min(TOP_K * n_queries, MAX_CONTEXT))
  MAX_CONTEXT     = "12" (max unique chunks kept for generation, mirrors local top-12)
  RETRIEVAL_MODE  = "dense" (default) | "hybrid"  (hybrid = BM25 + dense via RRF)
  BM25_WEIGHT     = "0.3" (default RRF BM25 weight, 0–1)
"""
from __future__ import annotations

import asyncio
import json
import os
import re
import ssl
import threading
import time
import urllib.error
import urllib.request
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Generator

import chromadb
import fitz  # PyMuPDF
import google.generativeai as genai
from app import bm25_index

# ── Ablation / tuning config ─────────────────────────────────────────────────
CHUNK_MODE:     str  = os.environ.get("CHUNK_MODE", "semantic").lower()   # "semantic" | "fixed"
EXPAND_ON:      bool = os.environ.get("EXPAND_ON", "1") not in ("0", "false", "no")
TOP_K:          int  = int(os.environ.get("TOP_K", "8"))
MAX_CONTEXT:    int  = int(os.environ.get("MAX_CONTEXT", "12"))
RETRIEVAL_MODE: str  = os.environ.get("RETRIEVAL_MODE", "dense").lower()  # "dense" | "hybrid"
BM25_WEIGHT:    float = float(os.environ.get("BM25_WEIGHT", "0.3"))       # RRF blend weight

# Fixed-size fallback params (used when CHUNK_MODE=fixed or as sub-split ceiling)
CHUNK_SIZE    = int(os.environ.get("CHUNK_SIZE", "1200"))
CHUNK_OVERLAP = int(os.environ.get("CHUNK_OVERLAP", "150"))

COLLECTION_NAME = "tlu_docs"

# Embedding REST (avoids legacy SDK 404)
GEMINI_EMBED_REST_MODEL = os.environ.get("GEMINI_EMBED_REST_MODEL", "gemini-embedding-2-preview")
LLM_MODEL = os.environ.get("LLM_MODEL", "models/gemini-flash-latest")
MAX_OUTPUT_TOKENS = int(os.environ.get("MAX_OUTPUT_TOKENS", "600"))

# ── System prompt (5-step, mirrors local_rag_service.dart) ───────────────────
SYSTEM_INSTRUCTION = (
    "Bạn là Chuyên gia Tư vấn Học vụ AI của Đại học Thăng Long (TLU).\n"
    "QUY TRÌNH XỬ LÝ CÂU HỎI:\n"
    "BƯỚC 1 - Phân tích & Định danh: Xác định mục tiêu câu hỏi. Kiểm tra xem quy định có "
    "phụ thuộc vào Khóa học (K) hay Ngành học không. Nếu tài liệu chia theo đối tượng mà bạn "
    "chưa biết đối tượng của User, hãy hỏi khéo léo để xác định.\n"
    "BƯỚC 2 - Kiểm tra Hiệu lực: Nếu thấy nhiều văn bản trùng lặp, hãy ưu tiên văn bản có "
    "ngày ban hành mới nhất (năm học 2025-2026). Nêu rõ sự thay đổi nếu có.\n"
    "BƯỚC 3 - Suy luận Logic: Kết nối các mốc thời gian để đưa ra dự đoán thông minh nếu "
    "tài liệu không ghi trực tiếp.\n"
    "BƯỚC 4 - Tổng hợp & Phản hồi: Trả lời ngắn gọn, trực diện. Sử dụng bullet points khi cần.\n"
    "BƯỚC 5 - Điều phối (Escalation): Nếu thông tin không có trong tài liệu hoặc câu hỏi quá "
    "phức tạp/nhạy cảm, hãy gợi ý liên hệ phòng ban phù hợp.\n\n"
    "LƯU Ý: Tuyệt đối không bịa đặt thông tin. Luôn giữ thái độ chuyên nghiệp, tận tâm."
)


# ── Path helpers ─────────────────────────────────────────────────────────────

def _data_dir() -> Path:
    return Path(os.environ.get("CHROMA_DATA_DIR", "/tmp/chroma"))


def _sources_dir() -> Path:
    d = Path(os.environ.get("SOURCES_DIR", "/data/sources"))
    d.mkdir(parents=True, exist_ok=True)
    return d


def _catalog_path() -> Path:
    d = _data_dir()
    d.mkdir(parents=True, exist_ok=True)
    return d / "document_catalog.json"


def _load_catalog() -> list[dict[str, Any]]:
    p = _catalog_path()
    if not p.exists():
        return []
    return json.loads(p.read_text(encoding="utf-8"))


def _save_catalog(items: list[dict[str, Any]]) -> None:
    _catalog_path().write_text(
        json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8"
    )


# ── Gemini configuration ──────────────────────────────────────────────────────

def configure_genai() -> None:
    key = os.environ.get("GEMINI_API_KEY", "")
    if not key:
        raise RuntimeError("GEMINI_API_KEY is not set")
    genai.configure(api_key=key)


# ── Embed rate limiter (shared across threads for parallel eval) ──────────────
_embed_rate_lock = threading.Lock()
_embed_last_t: list[float] = [0.0]   # mutable container so threads share one value

# ── Multi-key rotation (set GEMINI_API_KEY=key1,key2,key3 in .env) ────────────
_key_lock  = threading.Lock()
_key_index: list[int] = [0]          # current active key index


def _get_embed_keys() -> list[str]:
    """Return list of Gemini API keys from comma-separated GEMINI_API_KEY env var."""
    raw = os.environ.get("GEMINI_API_KEY", "")
    return [k.strip() for k in raw.split(",") if k.strip()]


def _rotate_key(failed_index: int) -> int | None:
    """Rotate to the next key. Returns new index, or None if all keys exhausted."""
    with _key_lock:
        keys = _get_embed_keys()
        if not keys:
            return None
        if _key_index[0] == failed_index:
            next_idx = (failed_index + 1) % len(keys)
            if next_idx == failed_index:
                return None  # only one key, can't rotate
            _key_index[0] = next_idx
        return _key_index[0]


def _current_key() -> str:
    with _key_lock:
        keys = _get_embed_keys()
        if not keys:
            raise RuntimeError("GEMINI_API_KEY is not set")
        return keys[_key_index[0] % len(keys)]


def _embed_wait() -> None:
    """Block until the minimum inter-embed interval has elapsed, then claim the slot."""
    min_sec = float(os.environ.get("GEMINI_EMBED_MIN_INTERVAL_SEC", "0.5"))
    if min_sec <= 0:
        return
    with _embed_rate_lock:
        now = time.monotonic()
        wait = min_sec - (now - _embed_last_t[0])
        if wait > 0:
            time.sleep(wait)
        _embed_last_t[0] = time.monotonic()


# ── Embedding via REST (avoids legacy SDK 404 on new models) ─────────────────

def _ssl_context() -> ssl.SSLContext:
    """Use certifi CA bundle — fixes CERTIFICATE_VERIFY_FAILED on macOS Homebrew Python."""
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        return ssl.create_default_context()


def _parse_embed_response(payload: dict[str, Any]) -> list[float]:
    emb = payload.get("embedding")
    if isinstance(emb, dict) and "values" in emb:
        return [float(x) for x in emb["values"]]
    if isinstance(emb, list):
        return [float(x) for x in emb]
    raise RuntimeError(f"Unexpected embed response keys: {list(payload.keys())}")


def _embed_via_rest(text: str, model: str | None = None) -> list[float]:
    _embed_wait()   # rate-limit shared across all threads
    keys = _get_embed_keys()
    if not keys:
        raise RuntimeError("GEMINI_API_KEY is not set")
    m = (model or GEMINI_EMBED_REST_MODEL).strip() or "gemini-embedding-2-preview"
    url = (
        "https://generativelanguage.googleapis.com/v1beta/"
        f"models/{m}:embedContent"
    )
    body: dict[str, Any] = {
        "model": f"models/{m}",
        "content": {"parts": [{"text": text}]},
    }
    dim_raw = os.environ.get("GEMINI_EMBED_OUTPUT_DIM", "").strip()
    if dim_raw.isdigit():
        body["outputDimensionality"] = int(dim_raw)

    # total attempts = retries per key × number of keys (rotate on 429)
    max_retries = max(1, int(os.environ.get("GEMINI_EMBED_MAX_RETRIES", "6")))
    base_delay  = float(os.environ.get("GEMINI_EMBED_RETRY_BASE_SEC", "2"))
    n_keys      = len(keys)

    last_err: str | None = None
    keys_tried: set[int] = set()
    for attempt in range(max_retries * n_keys):
        with _key_lock:
            key_idx = _key_index[0] % n_keys
            api_key = keys[key_idx]
        data = json.dumps(body).encode("utf-8")
        req  = urllib.request.Request(
            url, data=data, method="POST",
            headers={
                "Content-Type": "application/json; charset=utf-8",
                "x-goog-api-key": api_key,
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=120, context=_ssl_context()) as resp:
                payload = json.load(resp)
            return _parse_embed_response(payload)
        except urllib.error.HTTPError as e:
            err = e.read().decode("utf-8", errors="replace")
            last_err = f"embedContent HTTP {e.code}: {err}"
            if e.code == 429:
                keys_tried.add(key_idx)
                if len(keys_tried) < n_keys:
                    # Try next key immediately
                    new_idx = _rotate_key(key_idx)
                    if new_idx is not None:
                        print(f"  [KEY ROTATE] key[{key_idx}] quota hit → trying key[{new_idx}]")
                        continue
                # All keys tried → exponential backoff on current key
                if attempt < max_retries * n_keys - 1:
                    wait = base_delay * (2 ** min(attempt, 5))
                    time.sleep(min(wait, 60.0))
                    continue
            raise RuntimeError(last_err) from e
    raise RuntimeError(last_err or "embed failed")


def embed_batch(texts: list[str]) -> list[list[float]]:
    """Embed texts one-by-one with rate-limit delay. mirrors EmbeddingService.embedBatch()."""
    delay_ms = max(0, int(os.environ.get("EMBED_REQUEST_DELAY_MS", "400")))
    out: list[list[float]] = []
    for i, t in enumerate(texts):
        if i > 0 and delay_ms > 0:
            time.sleep(delay_ms / 1000.0)
        out.append(_embed_via_rest(t))
    return out


# ── ChromaDB ─────────────────────────────────────────────────────────────────

def get_chroma_client() -> chromadb.PersistentClient:
    path = str(_data_dir())
    _data_dir().mkdir(parents=True, exist_ok=True)
    return chromadb.PersistentClient(path=path)


def get_collection():
    client = get_chroma_client()
    return client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )


# ── Text extraction ───────────────────────────────────────────────────────────

def extract_text_from_pdf(data: bytes) -> str:
    doc = fitz.open(stream=data, filetype="pdf")
    parts: list[str] = []
    for page in doc:
        parts.append(page.get_text())
    doc.close()
    return "\n\n".join(parts)


def extract_text_from_bytes(data: bytes, filename: str) -> str:
    name = filename.lower()
    if name.endswith(".md") or name.endswith(".markdown"):
        return data.decode("utf-8", errors="replace")
    if name.endswith(".txt"):
        return data.decode("utf-8", errors="replace")
    if name.endswith(".pdf"):
        return extract_text_from_pdf(data)
    raise ValueError("Unsupported file type (use .pdf, .md, .txt)")


# ── Semantic Markdown Chunking (ported from pdf_service.dart) ─────────────────
# Strategy:
#   1. Split full text by Markdown headings (## or #).
#   2. Each (heading, content) section becomes one chunk if ≤ CHUNK_SIZE chars.
#   3. Sections exceeding CHUNK_SIZE are sub-split with table-awareness:
#      - Table lines (|...) are never broken mid-table.
#      - Context overlap = last 3 lines of previous sub-chunk (mirrors 3-line overlap).
#   4. Each chunk carries heading_path metadata for traceability.

def _split_by_headings(text: str) -> list[dict[str, str]]:
    """Split text into sections on ## or # markers."""
    sections: list[dict[str, str]] = []
    lines = text.split("\n")
    current_heading = ""
    current_lines: list[str] = []

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("##") or (stripped.startswith("#") and not stripped.startswith("##")):
            # Save previous section
            if current_lines or current_heading:
                sections.append({
                    "heading": current_heading,
                    "content": "\n".join(current_lines).strip(),
                })
            current_heading = stripped
            current_lines = []
        else:
            current_lines.append(line)

    # Last section
    if current_lines or current_heading:
        sections.append({
            "heading": current_heading,
            "content": "\n".join(current_lines).strip(),
        })

    return sections


def _split_sub_section(content: str, heading: str) -> list[str]:
    """Break an oversized section into sub-chunks, preserving tables and overlapping 3 lines."""
    sub_chunks: list[str] = []
    lines = content.split("\n")
    buffer: list[str] = []
    in_table = False

    for line in lines:
        is_table_line = line.strip().startswith("|")

        # Flush buffer if it would exceed CHUNK_SIZE, but not mid-table
        buffer_text = "\n".join(buffer)
        if len(buffer_text) + len(line) > CHUNK_SIZE and (not is_table_line or not in_table):
            prefix = f"{heading} (Tiếp theo)\n" if heading else ""
            sub_chunks.append(f"{prefix}{buffer_text.strip()}")

            # 3-line overlap for context continuity
            overlap_lines = buffer[-3:] if len(buffer) > 3 else buffer[:]
            buffer = overlap_lines[:]

        buffer.append(line)
        in_table = is_table_line

    if buffer:
        remaining = "\n".join(buffer).strip()
        if remaining:
            prefix = f"{heading} (Tiếp theo)\n" if heading else ""
            sub_chunks.append(f"{prefix}{remaining}")

    return sub_chunks if sub_chunks else [content]


def chunk_text_semantic(text: str, doc_id: str, doc_name: str) -> list[dict[str, Any]]:
    """Semantic Markdown Chunking — canonical strategy."""
    text = re.sub(r"\r\n", "\n", text).strip()
    if not text:
        return []

    chunks: list[dict[str, Any]] = []
    sections = _split_by_headings(text)
    idx = 0

    for section in sections:
        heading = section["heading"]
        content = section["content"]

        if not content.strip() and not heading.strip():
            continue

        if len(content) > CHUNK_SIZE:
            sub_list = _split_sub_section(content, heading)
            for sub in sub_list:
                if len(sub.strip()) > 20:
                    chunks.append({
                        "id": f"{doc_id}_{idx}",
                        "text": sub.strip(),
                        "meta": {
                            "doc_id": doc_id,
                            "doc_name": doc_name,
                            "chunk_index": idx,
                            "heading_path": heading,
                            "chunk_type": "sub",
                        },
                    })
                    idx += 1
        else:
            combined = f"{heading}\n{content}".strip() if heading else content.strip()
            if len(combined) > 20:
                chunks.append({
                    "id": f"{doc_id}_{idx}",
                    "text": combined,
                    "meta": {
                        "doc_id": doc_id,
                        "doc_name": doc_name,
                        "chunk_index": idx,
                        "heading_path": heading,
                        "chunk_type": "section",
                    },
                })
                idx += 1

    return chunks


def chunk_text_fixed(text: str, doc_id: str, doc_name: str) -> list[dict[str, Any]]:
    """Fixed-size sliding-window chunking (baseline for ablation)."""
    text = re.sub(r"\r\n", "\n", text).strip()
    if not text:
        return []
    chunks: list[dict[str, Any]] = []
    start = 0
    n = len(text)
    idx = 0
    while start < n:
        end = min(start + CHUNK_SIZE, n)
        piece = text[start:end]
        chunks.append({
            "id": f"{doc_id}_{idx}",
            "text": piece,
            "meta": {
                "doc_id": doc_id,
                "doc_name": doc_name,
                "chunk_index": idx,
                "heading_path": "",
                "chunk_type": "fixed",
            },
        })
        idx += 1
        if end >= n:
            break
        start = end - CHUNK_OVERLAP
        if start < 0:
            start = 0
    return chunks


def chunk_text(text: str, doc_id: str, doc_name: str) -> list[dict[str, Any]]:
    """Route to semantic or fixed chunking based on CHUNK_MODE env flag."""
    if CHUNK_MODE == "fixed":
        return chunk_text_fixed(text, doc_id, doc_name)
    return chunk_text_semantic(text, doc_id, doc_name)


# ── Ingest ────────────────────────────────────────────────────────────────────

def ingest_bytes(data: bytes, filename: str) -> dict[str, Any]:
    doc_id  = str(uuid.uuid4())
    raw     = extract_text_from_bytes(data, filename)

    sources  = _sources_dir()
    safe_name = re.sub(r"[^\w.\-]", "_", filename)[:120]
    (sources / f"{doc_id}_{safe_name}").write_bytes(data)
    (sources / f"{doc_id}.md").write_text(raw, encoding="utf-8")

    chunks = chunk_text(raw, doc_id, filename)
    if not chunks:
        raise ValueError("No text extracted from file")

    coll       = get_collection()
    embeddings = embed_batch([c["text"] for c in chunks])
    coll.add(
        ids=[c["id"] for c in chunks],
        embeddings=embeddings,
        documents=[c["text"] for c in chunks],
        metadatas=[c["meta"] for c in chunks],
    )

    catalog = _load_catalog()
    catalog.append({
        "id":          doc_id,
        "name":        filename,
        "chunk_count": len(chunks),
        "chunk_mode":  CHUNK_MODE,
        "created_at":  datetime.now(timezone.utc).isoformat(),
    })
    _save_catalog(catalog)

    # Rebuild BM25 index for hybrid retrieval support
    bm25_index.rebuild_from_collection(coll, _data_dir())

    return {"doc_id": doc_id, "name": filename, "chunk_count": len(chunks)}


def list_documents() -> list[dict[str, Any]]:
    return list(_load_catalog())


def delete_document(doc_id: str) -> bool:
    coll    = get_collection()
    catalog = _load_catalog()
    before  = len(catalog)
    catalog = [d for d in catalog if d["id"] != doc_id]
    if len(catalog) == before:
        return False
    _save_catalog(catalog)
    coll.delete(where={"doc_id": doc_id})
    bm25_index.rebuild_from_collection(coll, _data_dir())
    return True


# ── Query expansion (ported from _expandQuery in local_rag_service.dart) ──────

def expand_query(question: str) -> list[str]:
    """Generate 3-4 search keyword variants including abbreviation expansion.
    Falls back to [question] on any error (same as Dart catch block).
    """
    if not EXPAND_ON:
        return [question]

    try:
        configure_genai()
        prompt = (
            f'Bạn là chuyên gia tra cứu. Với câu hỏi: "{question}", hãy đưa ra 3-4 từ khóa '
            "tìm kiếm hiệu quả trong Sổ tay sinh viên. "
            "LƯU Ý VỀ CÁC TỪ VIẾT TẮT: IT = Công nghệ thông tin, SV = Sinh viên, "
            "HK = Học kỳ, HP = Học phần, CB = Cố vấn, ĐKH = Đăng ký học, "
            "CTĐT = Chương trình đào tạo, GPA = điểm trung bình tích lũy. "
            "Chỉ trả về các cụm từ cách nhau bởi dấu phẩy.\n"
            'Ví dụ: "ngành IT học gì" -> "Chương trình đào tạo Công nghệ thông tin, '
            'môn học IT, khung đào tạo Công nghệ thông tin"'
        )
        model = genai.GenerativeModel(LLM_MODEL)
        response = model.generate_content(prompt)
        text = (response.text or question).strip()
        variants = [s.strip() for s in text.split(",") if s.strip()]
        if question not in variants:
            variants.append(question)
        return variants[:5]  # cap at 5 to control quota
    except Exception:  # noqa: BLE001
        return [question]


# ── Reciprocal Rank Fusion ─────────────────────────────────────────────────────

def _rrf_fuse(
    dense_hits: list[dict[str, Any]],
    sparse_hits: list[dict[str, Any]],
    *,
    k: int = 60,
    dense_weight: float = 1.0,
    sparse_weight: float = 1.0,
) -> list[dict[str, Any]]:
    """Combine dense and sparse ranked lists via Reciprocal Rank Fusion (Cormack 2009).

    RRF score(d) = Σ w_i / (k + rank_i(d))
    k=60 is the standard constant that dampens the impact of high ranks.
    """
    scores: dict[str, float] = {}
    meta_map: dict[str, dict[str, Any]] = {}

    for rank, hit in enumerate(dense_hits, start=1):
        doc_id_key = hit.get("id") or hit["text"][:80]
        scores[doc_id_key] = scores.get(doc_id_key, 0.0) + dense_weight / (k + rank)
        meta_map[doc_id_key] = hit

    for rank, hit in enumerate(sparse_hits, start=1):
        doc_id_key = hit.get("id") or hit["text"][:80]
        scores[doc_id_key] = scores.get(doc_id_key, 0.0) + sparse_weight / (k + rank)
        if doc_id_key not in meta_map:
            meta_map[doc_id_key] = hit

    fused = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    return [
        {**meta_map[key], "score": round(score, 6)}
        for key, score in fused
    ]


# ── Retrieval: multi-query + dense|hybrid (mirrors queryStream in local_rag_service) ─

def retrieve_context(
    question: str,
    doc_id: str | None,
    top_k: int | None = None,
    max_context: int | None = None,
) -> tuple[str, str, list[dict[str, Any]]]:
    """Multi-query retrieval with dedup, returns (context_str, sources_str, raw_chunks).

    RETRIEVAL_MODE=dense  : cosine similarity via ChromaDB only.
    RETRIEVAL_MODE=hybrid : dense + BM25 fused with Reciprocal Rank Fusion (RRF).
    """
    k = top_k if top_k is not None else TOP_K
    mc = max_context if max_context is not None else MAX_CONTEXT

    queries = expand_query(question)
    coll = get_collection()
    where = {"doc_id": doc_id} if doc_id else None

    # ── Dense retrieval (always) ───────────────────────────────────────────────
    seen_texts: set[str] = set()
    dense_results: list[dict[str, Any]] = []

    for q in queries:
        qvec = _embed_via_rest(q)
        res  = coll.query(
            query_embeddings=[qvec],
            n_results=k,
            where=where,
            include=["documents", "metadatas", "distances"],
        )
        docs   = (res.get("documents") or [[]])[0]
        metas  = (res.get("metadatas")  or [[]])[0]
        dists  = (res.get("distances")  or [[]])[0]
        ids    = (res.get("ids")        or [[]])[0]  # ids returned by default, not in include

        for chunk_id, doc_text, meta, dist in zip(ids, docs, metas, dists):
            if doc_text not in seen_texts:
                seen_texts.add(doc_text)
                dense_results.append({
                    "id":    chunk_id,
                    "text":  doc_text,
                    "meta":  meta or {},
                    "score": 1.0 - float(dist),
                })

    dense_results.sort(key=lambda r: r["score"], reverse=True)

    # ── Hybrid: fuse with BM25 via RRF ────────────────────────────────────────
    if RETRIEVAL_MODE == "hybrid":
        bm25_hits = bm25_index.search(question, _data_dir(), top_k=k * 2, doc_id=doc_id)
        top_results = _rrf_fuse(
            dense_results,
            bm25_hits,
            dense_weight=1.0 - BM25_WEIGHT,
            sparse_weight=BM25_WEIGHT,
        )[:mc]
    else:
        top_results = dense_results[:mc]

    if not top_results:
        return "", "", []

    parts: list[str] = []
    names: set[str]  = set()
    for i, r in enumerate(top_results):
        name = r["meta"].get("doc_name", "unknown")
        names.add(str(name))
        parts.append(f"[Đoạn {i + 1} - {name}]\n{r['text']}")

    context = "\n\n---\n\n".join(parts)
    sources = ", ".join(sorted(list(names)[:3]))
    return context, sources, top_results


# ── Generation: streaming answer ──────────────────────────────────────────────

def build_generation_prompt(question: str, context: str, sources: str) -> str:
    """Xây dựng prompt generation chuẩn — dùng chung cho stream_answer() và eval."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return f"""Hôm nay: {now}.

Dữ liệu tài liệu:
---
{context}
---

Câu hỏi: "{question}"

Thực hiện phản hồi theo các nguyên tắc:
1. Trả lời súc tích, đi thẳng vào vấn đề. Ưu tiên các bảng biểu và mốc thời gian của năm học 2025-2026.
2. Nếu câu hỏi về môn học/chương trình đào tạo, hãy trình bày rõ ràng danh sách môn học tìm được.
3. Nếu thông tin có sự phân hóa theo đối tượng (K, Ngành), hãy chỉ rõ điều đó và hỏi thêm User nếu cần.
4. Nếu cảm thấy thông tin trong tài liệu không đủ hoặc không chắc chắn, hãy thực hiện Bước 5 trong Quy trình (Escalation).
5. Ghi nguồn: "📚 Nguồn: {sources}"
"""


NO_CONTEXT_REPLY = (
    "Không tìm thấy thông tin liên quan trong tài liệu. "
    "Hãy thử đặt câu hỏi khác hoặc nạp tài liệu mới nhất."
)


def stream_answer(
    question: str,
    doc_id: str | None,
    *,
    context: str | None = None,
    sources: str | None = None,
) -> Generator[str, None, None]:
    """Stream an answer. If context/sources are pre-fetched, pass them to avoid double retrieval."""
    configure_genai()
    if context is None:
        context, sources, _ = retrieve_context(question, doc_id)

    if not context:
        yield NO_CONTEXT_REPLY
        return

    prompt = build_generation_prompt(question, context, sources or "")
    model = genai.GenerativeModel(
        LLM_MODEL,
        system_instruction=SYSTEM_INSTRUCTION,
        generation_config=genai.types.GenerationConfig(
            temperature=0.1,
            max_output_tokens=MAX_OUTPUT_TOKENS,
        ),
    )
    for chunk in model.generate_content(prompt, stream=True):
        if chunk.text:
            yield chunk.text
