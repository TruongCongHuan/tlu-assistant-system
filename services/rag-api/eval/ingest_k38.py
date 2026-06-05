"""Ingest the K38 student handbook (guide_book_k38_pymupdf.md) into ChromaDB.

Usage (run from repo root, Docker backend must be running):
    python services/rag-api/eval/ingest_k38.py

Or run directly inside the rag-api container:
    docker exec -it <rag-api-container> python /app/eval/ingest_k38.py

Requires: GEMINI_API_KEY in environment (or .env), CHROMA_DATA_DIR pointing to
the persistent volume (defaults to /tmp/chroma in dev, /chroma-data in Docker).
"""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

# Allow running from repo root OR from inside the container
_here = Path(__file__).resolve().parent
_repo_root = _here.parent.parent.parent  # services/rag-api/eval -> repo root
sys.path.insert(0, str(_here.parent))    # add services/rag-api so `app` is importable

from dotenv import load_dotenv
load_dotenv(_repo_root / ".env", override=False)

import app.rag as rag  # noqa: E402  (after sys.path manipulation)

CORPUS_PATH = _repo_root / "output_md" / "guide_book_k38_pymupdf.md"


def main() -> None:
    if not CORPUS_PATH.exists():
        print(f"[ERROR] Corpus not found: {CORPUS_PATH}")
        sys.exit(1)

    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        print("[ERROR] GEMINI_API_KEY is not set. Add it to .env or export it.")
        sys.exit(1)

    print(f"[INFO] Corpus: {CORPUS_PATH} ({CORPUS_PATH.stat().st_size // 1024} KB)")
    print(f"[INFO] CHUNK_MODE={rag.CHUNK_MODE}  TOP_K={rag.TOP_K}  EXPAND_ON={rag.EXPAND_ON}")
    print("[INFO] Starting ingest … (this takes ~5-10 min on free-tier Gemini)")

    data     = CORPUS_PATH.read_bytes()
    filename = CORPUS_PATH.name
    t0       = time.time()

    result = rag.ingest_bytes(data, filename)

    elapsed = time.time() - t0
    print(
        f"[OK] Ingested '{result['name']}' "
        f"doc_id={result['doc_id']}  chunks={result['chunk_count']}  "
        f"elapsed={elapsed:.1f}s"
    )


if __name__ == "__main__":
    main()
