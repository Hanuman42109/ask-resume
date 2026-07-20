from dotenv import load_dotenv
load_dotenv()

import os
import asyncpg
from nomic import embed

# Configuration
DATABASE_URL  = os.getenv("DATABASE_URL", "postgresql://user:password@localhost:5432/resume_db")
CHUNK_SIZE    = 400
CHUNK_OVERLAP = 80
EMBED_MODEL   = "nomic-embed-text-v1.5"
EMBEDDING_DIM = 768

# Local embedding fallback for development
USE_LOCAL_EMBED = os.getenv("USE_LOCAL_EMBED", "false").lower() == "true"
if USE_LOCAL_EMBED:
    from sentence_transformers import SentenceTransformer
    embedder = SentenceTransformer("all-mpnet-base-v2")
    EMBEDDING_DIM = 768
    print(f"[ingest] Using local embeddings (SentenceTransformers/all-mpnet-base-v2) — dim={EMBEDDING_DIM}")
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
        print(f"[ingest] Computing local embeddings for {len(chunks)} chunks...")
        embeddings = embedder.encode(chunks, convert_to_numpy=True)
        return [emb.flatten().tolist() for emb in embeddings]
    
    # Use Nomic AI for stable embedding generation
    print(f"[ingest] Getting Nomic embeddings for {len(chunks)} chunks...")
    try:
        output = embed.text(
            texts=chunks,
            model=EMBED_MODEL,
            task_type="search_document"
        )
        return output['embeddings']
    except Exception as e:
        print(f"[ingest] Nomic API Error: {str(e)}")
        raise e

async def ingest_documents(text: str, source: str) -> int:
    try:
        chunks = chunk_text(text)
        if not chunks:
            return 0

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
                # Format embedding as a vector string for pgvector
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