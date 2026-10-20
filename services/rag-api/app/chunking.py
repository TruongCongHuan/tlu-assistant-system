"""Shared deterministic chunking; usable without API keys or vector DB dependencies."""
from __future__ import annotations

import re
from typing import Any

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


def _split_sub_section(content: str, heading: str, chunk_size: int = 1200) -> list[str]:
    """Break an oversized section into sub-chunks, preserving tables and overlapping 3 lines."""
    sub_chunks: list[str] = []
    lines = content.split("\n")
    buffer: list[str] = []
    in_table = False

    for line in lines:
        is_table_line = line.strip().startswith("|")

        # Flush buffer if it would exceed chunk_size, but not mid-table
        buffer_text = "\n".join(buffer)
        if len(buffer_text) + len(line) > chunk_size and (not is_table_line or not in_table):
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


def chunk_text_semantic(text: str, doc_id: str, doc_name: str, chunk_size: int = 1200) -> list[dict[str, Any]]:
    """Semantic Markdown Chunking — canonical strategy."""
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")
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

        if len(content) > chunk_size:
            sub_list = _split_sub_section(content, heading, chunk_size)
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


def chunk_text_fixed(text: str, doc_id: str, doc_name: str, chunk_size: int = 1200, chunk_overlap: int = 150) -> list[dict[str, Any]]:
    """Fixed-size sliding-window chunking (baseline for ablation)."""
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")
    text = re.sub(r"\r\n", "\n", text).strip()
    if not text:
        return []
    chunks: list[dict[str, Any]] = []
    if not 0 <= chunk_overlap < chunk_size:
        raise ValueError("chunk_overlap must be smaller than chunk_size")
    start = 0
    n = len(text)
    idx = 0
    while start < n:
        end = min(start + chunk_size, n)
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
        start = end - chunk_overlap
        if start < 0:
            start = 0
    return chunks

