"""
RAG Pipeline
- Embeds questions using sentence-transformers (free, local)
- Retrieves top-k similar chunks from pgvector
- Streams answers from Groq (free)
"""

import os
from typing import AsyncGenerator

import asyncpg
from dotenv import load_dotenv
EMBEDDING_MODEL = "text-embedding-3-small"

# Client for Groq (LLM)
client = AsyncOpenAI(
    api_key=GROQ_API_KEY,
    base_url="https://api.groq.com/openai/v1",
)

# Client for OpenAI (Embeddings)
openai_client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

SYSTEM_PROMPT = """You are a helpful assistant representing Sai's professional portfolio.
Answer questions about Sai's skills, experience, and projects based ONLY on the context provided.
Be concise, specific, and honest. If you cannot find the answer in the context, say so clearly.
Never fabricate experience or skills not present in the context.
Speak in third person about Sai (e.g. "Sai has experience with...").
"""


class RAGPipeline:

    # ── Embed ──────────────────────────────────────────────────────────────────

    async def embed(self, text: str) -> list[float]:
        response = await openai_client.embeddings.create(
            input=text,
            model=EMBEDDING_MODEL
        )
        return response.data[0].embedding

    # ── Retrieve ───────────────────────────────────────────────────────────────

    async def retrieve(self, question: str, top_k: int = TOP_K) -> list[dict]:
        q_embedding = await self.embed(question)
        embedding_str = f"[{','.join(map(str, q_embedding))}]"

        conn = await asyncpg.connect(DATABASE_URL)
        try:
            rows = await conn.fetch(
                """
                SELECT id, content, source, chunk_index,
                       1 - (embedding <=> $1::vector) AS similarity
                FROM resume_chunks
                ORDER BY embedding <=> $1::vector
                LIMIT $2
                """,
                embedding_str,
                top_k,
            )
            return [dict(r) for r in rows]
        finally:
            await conn.close()

    # ── Stream from pre-retrieved chunks ───────────────────────────────────────

    async def stream_from_chunks(
        self,
        question: str,
        chunks: list[dict],
        history: list[dict],
    ) -> AsyncGenerator[str, None]:
        context = "\n\n---\n\n".join(
            f"[Source: {c['source']} | Chunk {c['chunk_index']}]\n{c['content']}"
            for c in chunks
        )

        messages = [
            *history[-6:],
            {
                "role": "user",
                "content": (
                    f"Context from Sai's resume/portfolio:\n\n{context}"
                    f"\n\n---\n\nQuestion: {question}"
                ),
            },
        ]

        stream = await client.chat.completions.create(
            model=CHAT_MODEL,
            messages=[{"role": "system", "content": SYSTEM_PROMPT}, *messages],
            max_tokens=MAX_TOKENS,
            stream=True,
            temperature=0.3,
        )

        async for chunk in stream:
            delta = chunk.choices[0].delta.content
            if delta:
                yield delta

    # ── Debug ──────────────────────────────────────────────────────────────────

    async def list_chunks(self) -> list[dict]:
        conn = await asyncpg.connect(DATABASE_URL)
        try:
            rows = await conn.fetch(
                "SELECT id, source, chunk_index, LEFT(content, 100) AS preview FROM resume_chunks ORDER BY id"
            )
            return [dict(r) for r in rows]
        finally:
            await conn.close()
