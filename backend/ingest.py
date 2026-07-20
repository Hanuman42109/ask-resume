import os
import asyncpg
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer

load_dotenv()

DATABASE_URL  = os.getenv("DATABASE_URL", "postgresql://user:password@localhost:5432/resume_db")

CHUNK_SIZE    = 400
CHUNK_OVERLAP = 80
EMBEDDING_DIM = 384

embedder = SentenceTransformer("all-MiniLM-L6-v2")

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
        if chunk: chunks.append(chunk)
        start = end - overlap
    return chunks

async def ingest_documents(text: str, source: str) -> int:
    try:
        chunks = chunk_text(text)
        if not chunks: return 0

        print(f"[ingest] Getting local embeddings for {len(chunks)} chunks...")
        embeddings = embedder.encode(chunks, convert_to_numpy=True).tolist()
        print(f"[ingest] Received {len(embeddings)} embeddings")

        conn = await asyncpg.connect(DATABASE_URL)
        try:
            # We must DROP the table or change the dimension because 384 != 768
            await conn.execute("DROP TABLE IF EXISTS resume_chunks;")
            await conn.execute("CREATE EXTENSION IF NOT EXISTS vector;")
            await conn.execute(f"CREATE TABLE resume_chunks (id SERIAL PRIMARY KEY, source TEXT NOT NULL, chunk_index INTEGER NOT NULL, content TEXT NOT NULL, embedding vector({EMBEDDING_DIM}), created_at TIMESTAMPTZ DEFAULT now(), UNIQUE(source, chunk_index));")

            for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
                vector_str = f"[{','.join(map(str, embedding))}]"
                await conn.execute(
                    "INSERT INTO resume_chunks (source, chunk_index, content, embedding) VALUES ($1, $2, $3, $4::vector)",
                    source, i, chunk, vector_str
                )

            print(f"[ingest] Success — {len(chunks)} chunks stored using Groq.")
            return len(chunks)
        finally:
            await conn.close()
    except Exception as e:
        print(f"[ingest] CRITICAL ERROR: {str(e)}")
        return 0
