"""
Ask My Resume - FastAPI RAG Backend
Stack: FastAPI + pgvector + sentence-transformers + Groq streaming
"""

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import json
from typing import AsyncGenerator

from rag import RAGPipeline
from ingest import ingest_documents

app = FastAPI(title="Ask My Resume API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

rag = RAGPipeline()


# ── Request / Response models ──────────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str
    conversation_history: list[dict] = []


class IngestRequest(BaseModel):
    text: str
    source: str = "resume"


# ── Routes ─────────────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/ingest")
async def ingest(req: IngestRequest):
    try:
        chunk_count = await ingest_documents(req.text, req.source)
        return {"message": f"Ingested {chunk_count} chunks from '{req.source}'"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/chat")
async def chat(req: ChatRequest):
    """
    Stream a RAG-powered response.
    SSE event types:
      - { type: "citations", chunks: [...] }  — sent first, before tokens
      - { type: "token", value: "..." }        — streamed tokens
      - { type: "done" }                       — end of stream
      - { type: "error", message: "..." }      — on failure
    """
    async def event_stream() -> AsyncGenerator[str, None]:
        try:
            # 1. Retrieve chunks first and send as citations event
            chunks = await rag.retrieve(req.message)
            citations = [
                {"source": c["source"], "chunk_index": c["chunk_index"], "preview": c["content"][:120]}
                for c in chunks
            ]
            yield f"data: {json.dumps({'type': 'citations', 'chunks': citations})}\n\n"

            # 2. Stream tokens
            async for token in rag.stream_from_chunks(
                question=req.message,
                chunks=chunks,
                history=req.conversation_history,
            ):
                yield f"data: {json.dumps({'type': 'token', 'value': token})}\n\n"

            yield f"data: {json.dumps({'type': 'done'})}\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@app.get("/chunks")
async def list_chunks():
    chunks = await rag.list_chunks()
    return {"chunks": chunks}
