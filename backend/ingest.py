"""
Document Ingestion Pipeline
1. Split text into overlapping chunks
2. Embed each chunk using sentence-transformers (free, local)
3. Upsert into PostgreSQL with pgvector
"""

import os
import asyncpg
from openai import AsyncOpenAI

DATABASE_URL  = os.getenv("DATABASE_URL", "postgresql://user:password@localhost:5432/resume_db")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

CHUNK_SIZE    = 400
CHUNK_OVERLAP = 80

EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIM = 1536

openai_client = AsyncOpenAI(api_key=OPENAI_API_KEY)


def chunk_text(text: str, size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    text = " ".join(text.split())
    chunks = []
    start = 0
    while start < len(text):
        end = start + size
        if end < len(text):
            for boundary in [".", "!", "?"]:
                pos = text.rfind(boundary, start + overlap, end)
                if pos != -1:
                    end = pos + 1
                    break
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        start = end - overlap
    return chunks


async def setup_db(conn: asyncpg.Connection):
    await conn.execute("CREATE EXTENSION IF NOT EXISTS vector;")
    await conn.execute(f"""
        CREATE TABLE IF NOT EXISTS resume_chunks (
            id          SERIAL PRIMARY KEY,
            source      TEXT NOT NULL,
            chunk_index INTEGER NOT NULL,
            content     TEXT NOT NULL,
            embedding   vector({EMBEDDING_DIM}),
            created_at  TIMESTAMPTZ DEFAULT now(),
            UNIQUE(source, chunk_index)
        );
    """)
    await conn.execute("""
        CREATE INDEX IF NOT EXISTS resume_chunks_embedding_idx
        ON resume_chunks
        USING ivfflat (embedding vector_cosine_ops)
        WITH (lists = 50);
    """)


async def ingest_documents(text: str, source: str) -> int:
    chunks = chunk_text(text)
    if not chunks:
        return 0

    print(f"[ingest] {len(chunks)} chunks from '{source}'")

    # Embed all chunks using OpenAI API
    res = await openai_client.embeddings.create(
        input=chunks,
        model=EMBEDDING_MODEL
    )
    embeddings = [e.embedding for e in res.data]

    conn = await asyncpg.connect(DATABASE_URL)
    try:
        await setup_db(conn)
        await conn.execute("DELETE FROM resume_chunks WHERE source = $1", source)

        for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            embedding_str = f"[{','.join(map(str, embedding))}]"
            await conn.execute(
                """
                INSERT INTO resume_chunks (source, chunk_index, content, embedding)
                VALUES ($1, $2, $3, $4::vector)
                ON CONFLICT (source, chunk_index) DO UPDATE
                    SET content = EXCLUDED.content,
                        embedding = EXCLUDED.embedding
                """,
                source, i, chunk, embedding_str,
            )

        print(f"[ingest] Done — {len(chunks)} chunks stored.")
        return len(chunks)
    finally:
        await conn.close()
