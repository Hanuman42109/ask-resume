from dotenv import load_dotenv
load_dotenv()

import os
import httpx
import asyncpg

DATABASE_URL  = os.getenv("DATABASE_URL", "postgresql://user:password@localhost:5432/resume_db")
HF_TOKEN      = os.getenv("HF_TOKEN")
HF_MODEL      = "sentence-transformers/all-MiniLM-L6-v2"
CHUNK_SIZE    = 400
CHUNK_OVERLAP = 80
EMBEDDING_DIM = 384

# Local embedding fallback for development (no network needed)
USE_LOCAL_EMBED = os.getenv("USE_LOCAL_EMBED", "false").lower() == "true"
if USE_LOCAL_EMBED:
    from sentence_transformers import SentenceTransformer
    embedder = SentenceTransformer("all-MiniLM-L6-v2")
    print("[ingest] Using local embeddings (SentenceTransformers)")
else:
    embedder = None


def chunk_text(text: str) -> list[str]:
    text = " ".join(text.split())
    chunks = []
    start = 0
    while start < len(text):
        end = start + CHUNK_SIZE
        if end < len(text):
            for boundary in [".", "!", "?"]:
                pos = text.rfind(boundary, start + CHUNK_OVERLAP, end)
                if pos != -1:
                    end = pos + 1
                    break
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        start = end - CHUNK_OVERLAP
    return chunks


async def get_embeddings(chunks: list[str]) -> list[list[float]]:
    if USE_LOCAL_EMBED:
        # Local embeddings - synchronous, no network needed
        print(f"[ingest] Computing local embeddings for {len(chunks)} chunks...")
        embeddings = embedder.encode(chunks, convert_to_numpy=True)
        result = [emb.flatten().tolist() for emb in embeddings]
        print(f"[ingest] Generated {len(result)} embeddings locally")
        return result
    
    # HuggingFace API fallback
    async with httpx.AsyncClient() as client:
        res = await client.post(
            f"https://api-inference.huggingface.co/pipeline/feature-extraction/{HF_MODEL}",
            headers={"Authorization": f"Bearer {HF_TOKEN}"},
            json={"inputs": chunks, "options": {"wait_for_model": True}},
            timeout=60,
        )
        result = res.json()
        print(f"[ingest] HF response type: {type(result)}, length: {len(result)}")
        return result


async def ingest_documents(text: str, source: str) -> int:
    try:
        chunks = chunk_text(text)
        if not chunks:
            return 0

        print(f"[ingest] Getting HuggingFace embeddings for {len(chunks)} chunks...")
        embeddings = await get_embeddings(chunks)
        print(f"[ingest] Received {len(embeddings)} embeddings")

        conn = await asyncpg.connect(DATABASE_URL)
        try:
            await conn.execute("CREATE EXTENSION IF NOT EXISTS vector;")
            await conn.execute("DROP TABLE IF EXISTS resume_chunks;")
            await conn.execute(f"""
                CREATE TABLE resume_chunks (
                    id          SERIAL PRIMARY KEY,
                    source      TEXT NOT NULL,
                    chunk_index INTEGER NOT NULL,
                    content     TEXT NOT NULL,
                    embedding   vector({EMBEDDING_DIM}),
                    created_at  TIMESTAMPTZ DEFAULT now(),
                    UNIQUE(source, chunk_index)
                );
            """)

            for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
                vector_str = "[" + ",".join(map(str, embedding)) + "]"
                await conn.execute(
                    "INSERT INTO resume_chunks (source, chunk_index, content, embedding) VALUES ($1, $2, $3, $4::vector)",
                    source, i, chunk, vector_str
                )

            print(f"[ingest] Done — {len(chunks)} chunks stored for '{source}'")
            return len(chunks)
        finally:
            await conn.close()

    except Exception as e:
        print(f"[ingest] CRITICAL ERROR: {str(e)}")
        raise e