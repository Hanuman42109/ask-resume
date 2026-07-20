from dotenv import load_dotenv
load_dotenv()

import os
import asyncpg
from openai import AsyncOpenAI
from typing import AsyncGenerator

DATABASE_URL  = os.getenv("DATABASE_URL", "postgresql://user:password@localhost:5432/resume_db")
GROQ_API_KEY  = os.getenv("GROQ_API_KEY")
CHAT_MODEL    = os.getenv("CHAT_MODEL", "llama-3.3-70b-versatile")
EMBED_MODEL   = "nomic-embed-text-v1_5"
EMBEDDING_DIM = None
TOP_K         = 5
MAX_TOKENS    = 1024

# Local embedding fallback for development (no network needed)
USE_LOCAL_EMBED = os.getenv("USE_LOCAL_EMBED", "false").lower() == "true"
if USE_LOCAL_EMBED:
    from sentence_transformers import SentenceTransformer
    embedder = SentenceTransformer("all-MiniLM-L6-v2")
    try:
        EMBEDDING_DIM = embedder.get_sentence_embedding_dimension()
    except Exception:
        EMBEDDING_DIM = len(embedder.encode("test", convert_to_numpy=True))
    print(f"[rag] Using local embeddings (SentenceTransformers) — dim={EMBEDDING_DIM}")
else:
    embedder = None
    if EMBEDDING_DIM is None:
        EMBEDDING_DIM = 768

client = AsyncOpenAI(
    api_key=GROQ_API_KEY,
    base_url="https://api.groq.com/openai/v1",
)

SYSTEM_PROMPT = """You are a helpful assistant for Sai's professional portfolio.
Answer questions about Sai's skills, experience, and projects using ONLY the provided context.
Be specific and honest. If the answer is not in the context, say so clearly.
Always refer to Sai in third person (e.g. "Sai has worked with...").
"""


class RAGPipeline:

    async def embed(self, text: str) -> list[float]:
        if USE_LOCAL_EMBED:
            # Local embedding - synchronous, no network needed
            embedding = embedder.encode(text, convert_to_numpy=True)
            return embedding.flatten().tolist()

        # Use Groq embeddings via the AsyncOpenAI client
        response = await client.embeddings.create(
            model=EMBED_MODEL,
            input=text,
        )
        return response.data[0].embedding

    async def retrieve_chunks(self, query_vector: list[float]) -> list[dict]:
        conn = await asyncpg.connect(DATABASE_URL)
        try:
            vector_str = "[" + ",".join(map(str, query_vector)) + "]"
            rows = await conn.fetch("""
                SELECT id, source, chunk_index, content,
                       (1 - (embedding <=> $1::vector))::float AS similarity
                FROM resume_chunks
                ORDER BY embedding <=> $1::vector
                LIMIT $2
            """, vector_str, TOP_K)

            results = [dict(r) for r in rows]
            if results:
                print(f"[retrieve] {len(results)} chunks, top similarity: {results[0]['similarity']:.3f}")
            return results
        finally:
            await conn.close()

    async def stream_answer(
        self,
        question: str,
        context: str,
        history: list[dict],
    ) -> AsyncGenerator[str, None]:
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            *history[-4:],
            {"role": "user", "content": f"Context:\n\n{context}\n\n---\n\nQuestion: {question}"},
        ]

        stream = await client.chat.completions.create(
            model=CHAT_MODEL,
            messages=messages,
            max_tokens=MAX_TOKENS,
            stream=True,
            temperature=0.3,
        )

        async for chunk in stream:
            delta = chunk.choices[0].delta.content
            if delta:
                yield delta

    async def list_chunks(self) -> list[dict]:
        conn = await asyncpg.connect(DATABASE_URL)
        try:
            rows = await conn.fetch(
                "SELECT id, source, chunk_index, LEFT(content, 100) AS preview FROM resume_chunks ORDER BY id"
            )
            return [dict(r) for r in rows]
        finally:
            await conn.close()