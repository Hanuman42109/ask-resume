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
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

rag = RAGPipeline()


class ChatRequest(BaseModel):
    message: str
    conversation_history: list[dict] = []


class IngestRequest(BaseModel):
    text: str
    source: str = "resume"


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/ingest")
async def ingest(req: IngestRequest):
    try:
        count = await ingest_documents(req.text, req.source)
        return {"message": f"Ingested {count} chunks from '{req.source}'"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/chat")
async def chat(req: ChatRequest):
    async def event_stream() -> AsyncGenerator[str, None]:
        try:
            # 1. Embed the question
            query_vector = await rag.embed(req.message)

            # 2. Retrieve chunks and send citations
            chunks = await rag.retrieve_chunks(query_vector)
            citations = [
                {"source": c["source"], "chunk_index": c["chunk_index"], "preview": c["content"][:120]}
                for c in chunks
            ]
            yield f"data: {json.dumps({'type': 'citations', 'chunks': citations})}\n\n"

            # 3. Clean history — only role + content
            clean_history = [
                {"role": m["role"], "content": m["content"]}
                for m in req.conversation_history
                if m.get("content")
            ]

            # 4. Stream answer
            context = "\n\n---\n\n".join(
                f"[{c['source']} | chunk {c['chunk_index']}]\n{c['content']}"
                for c in chunks
            )
            async for token in rag.stream_answer(req.message, context, clean_history):
                yield f"data: {json.dumps({'type': 'token', 'value': token})}\n\n"

            yield f"data: {json.dumps({'type': 'done'})}\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@app.get("/chunks")
async def list_chunks():
    chunks = await rag.list_chunks()
    return {"chunks": chunks}