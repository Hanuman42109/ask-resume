from dotenv import load_dotenv
load_dotenv()

import os
from typing import AsyncGenerator

import asyncpg
from openai import AsyncOpenAI
from sentence_transformers import SentenceTransformer

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@localhost:5432/resume_db")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
CHAT_MODEL   = os.getenv("CHAT_MODEL", "llama-3.3-70b-versatile")
TOP_K        = 5
MAX_TOKENS   = 1024

embedder = SentenceTransformer("all-MiniLM-L6-v2")

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

    async def retrieve(self, question: str) -> list[dict]:
        embedding = embedder.encode(question).tolist()
        emb_str = "[" + ",".join(map(str, embedding)) + "]"

        conn = await asyncpg.connect(DATABASE_URL)
        try:
            # Use exact cosine similarity with parameterized query
            rows = await conn.fetch("""
                SELECT id, source, chunk_index, content,
                       (1 - (embedding <=> $1::vector))::float AS similarity
                FROM resume_chunks
                ORDER BY embedding <=> $1::vector
                LIMIT $2
            """, emb_str, TOP_K)

            results = [dict(r) for r in rows]
            top_sim = f"{results[0]['similarity']:.3f}" if results else "N/A"
            print(f"[retrieve] Found {len(results)} chunks, top similarity: {top_sim}")
            return results
        finally:
            await conn.close()

    async def stream_answer(
        self,
        question: str,
        chunks: list[dict],
        history: list[dict],
    ) -> AsyncGenerator[str, None]:

        if not chunks:
            context = "No context available."
        else:
            context = "\n\n---\n\n".join(
                f"[{c['source']} | chunk {c['chunk_index']}]\n{c['content']}"
                for c in chunks
            )

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            *history[-4:],
            {
                "role": "user",
                "content": f"Context:\n\n{context}\n\n---\n\nQuestion: {question}"
            },
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
