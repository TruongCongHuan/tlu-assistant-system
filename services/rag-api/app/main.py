"""FastAPI application: admin RAG + student chat (SSE)."""
from __future__ import annotations

import json
import os
import uuid
from typing import Any

from fastapi import BackgroundTasks, Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.auth import require_admin, require_student
from app import rag

app = FastAPI(title="TLU RAG API", version="1.0.0")

_origins = os.environ.get("CORS_ORIGINS", "*")
_cors_list = [o.strip() for o in _origins.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_list if _cors_list != ["*"] else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

JOBS: dict[str, dict[str, Any]] = {}


class ChatBody(BaseModel):
    question: str = Field(..., min_length=1, max_length=8000)
    doc_id: str | None = None


def _run_ingest_sync(job_id: str, data: bytes, filename: str) -> None:
    try:
        result = rag.ingest_bytes(data, filename)
        JOBS[job_id] = {
            "status": "completed",
            "doc_id": result["doc_id"],
            "name": result["name"],
            "chunk_count": result["chunk_count"],
            "error": None,
        }
    except Exception as e:  # noqa: BLE001
        JOBS[job_id] = {
            "status": "failed",
            "doc_id": None,
            "name": filename,
            "chunk_count": 0,
            "error": str(e),
        }


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/admin/documents", dependencies=[Depends(require_admin)])
async def admin_upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
) -> dict[str, Any]:
    if not file.filename:
        raise HTTPException(status_code=400, detail="Missing filename")
    data = await file.read()
    if len(data) == 0:
        raise HTTPException(status_code=400, detail="Empty file")
    job_id = str(uuid.uuid4())
    JOBS[job_id] = {
        "status": "pending",
        "doc_id": None,
        "name": file.filename,
        "chunk_count": 0,
        "error": None,
    }

    def task() -> None:
        JOBS[job_id]["status"] = "running"
        _run_ingest_sync(job_id, data, file.filename or "upload")

    background_tasks.add_task(task)
    return {"job_id": job_id, "filename": file.filename}


@app.get("/admin/ingest-jobs/{job_id}", dependencies=[Depends(require_admin)])
def admin_get_job(job_id: str) -> dict[str, Any]:
    job = JOBS.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return {"job_id": job_id, **job}


@app.get("/admin/documents", dependencies=[Depends(require_admin)])
def admin_list_documents() -> dict[str, Any]:
    return {"documents": rag.list_documents()}


@app.delete("/admin/documents/{doc_id}", dependencies=[Depends(require_admin)])
def admin_delete_document(doc_id: str) -> dict[str, Any]:
    ok = rag.delete_document(doc_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Document not found")
    return {"deleted": True, "doc_id": doc_id}


@app.post("/v1/chat/stream", dependencies=[Depends(require_student)])
def student_chat_stream(body: ChatBody) -> StreamingResponse:
    def gen():
        try:
            for piece in rag.stream_answer(body.question, body.doc_id):
                payload = json.dumps({"text": piece}, ensure_ascii=False)
                yield f"data: {payload}\n\n"
            yield "data: [DONE]\n\n"
        except Exception as e:  # noqa: BLE001
            err = json.dumps({"error": str(e)}, ensure_ascii=False)
            yield f"data: {err}\n\n"

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
