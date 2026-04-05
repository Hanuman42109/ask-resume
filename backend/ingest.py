from dotenv import load_dotenv
load_dotenv()

import os
import asyncpg
from sentence_transformers import SentenceTransformer

DATABASE_URL  = os.getenv("DATABASE_URL", "postgresql://user:password@localhost:5432/resume_db")
CHUNK_SIZE    = 400
CHUNK_OVERLAP = 80
EMBEDDING_DIM = 384

embedder = SentenceTransformer("all-MiniLM-L6-v2")


def chunk_text(text: str) -> list[str]:
    text = " ".join(text.split())
    chunks = []
    start = 0
    while start < len(text):
        end = start + CHUNK_SIZE
        if end < len(text):
            for b in [".", "!", "?"]:
                pos = text.rfind(b, start + CHUNK_OVERLAP, end)
                if pos != -1:
                    end = pos + 1
                    break
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        start = end - CHUNK_OVERLAP
    return chunks


async def setup_db(conn):
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
    # Create index only if table has data
    await conn.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_indexes
                WHERE indexname = 'resume_chunks_embedding_idx'
            ) THEN
                IF (SELECT COUNT(*) FROM resume_chunks) >= 10 THEN
                    EXECUTE 'CREATE INDEX resume_chunks_embedding_idx
                             ON resume_chunks
                             USING ivfflat (embedding vector_cosine_ops)
                             WITH (lists = 10)';
                END IF;
            END IF;
        END $$;
    """)


async def ingest_documents(text: str, source: str) -> int:
    chunks = chunk_text(text)
    if not chunks:
        return 0

    print(f"[ingest] Embedding {len(chunks)} chunks...")
    embeddings = embedder.encode(chunks, show_progress_bar=False).tolist()

    conn = await asyncpg.connect(DATABASE_URL)
    try:
        await setup_db(conn)
        await conn.execute("DELETE FROM resume_chunks WHERE source = $1", source)

        for i, (chunk, emb) in enumerate(zip(chunks, embeddings)):
            emb_str = "[" + ",".join(map(str, emb)) + "]"
            await conn.execute("""
                INSERT INTO resume_chunks (source, chunk_index, content, embedding)
                VALUES ($1, $2, $3, $4::vector)
                ON CONFLICT (source, chunk_index) DO UPDATE
                    SET content = EXCLUDED.content,
                        embedding = EXCLUDED.embedding
            """, source, i, chunk, emb_str)

        print(f"[ingest] Done — {len(chunks)} chunks stored for '{source}'")
        return len(chunks)
    finally:
        await conn.close()
