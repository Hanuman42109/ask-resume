# Ask My Resume — RAG Portfolio Chatbot

A production-ready RAG application that lets anyone chat with your resume/portfolio.
Built with **FastAPI + pgvector + OpenAI + React + TypeScript**.

```
┌─────────────────────────────────────────────────────────┐
│  User question                                          │
│       │                                                 │
│       ▼                                                 │
│  [Embed question] ──► pgvector cosine search            │
│                              │                          │
│                    Top-K relevant chunks                │
│                              │                          │
│                    [LLM: GPT-4o / Claude]               │
│                              │                          │
│                    Streamed answer ──► React UI         │
└─────────────────────────────────────────────────────────┘
```

## Stack

| Layer       | Tech                                    |
|-------------|-----------------------------------------|
| Frontend    | React + Vite + SSE streaming            |
| Backend     | FastAPI (Python)                        |
| Vector DB   | PostgreSQL + pgvector                   |
| Embeddings  | OpenAI `text-embedding-3-small`         |
| LLM         | GPT-4o (or Claude via env var)          |
| Deploy      | Vercel (FE) + Railway/Render (BE)       |

---

## Quick Start

### 1. Start PostgreSQL with pgvector

```bash
docker-compose up -d
```

### 2. Backend setup

This project uses Python 3.11 with a single backend environment named `.venv311`.

```bash
cd backend
python3.11 -m venv .venv311
source .venv311/bin/activate       # Windows: .venv311\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
# Edit .env — add your OPENAI_API_KEY

uvicorn main:app --reload --port 8000
```

If you previously created older folders such as `venv/` or `.venv/`, you can remove them to avoid confusion.

### 3. Frontend setup

```bash
cd frontend
npm install
npm run dev
# → http://localhost:5173
```

### 4. Ingest your resume

Open the app, click **"⊕ ingest docs"**, paste your resume text, click **"Ingest & embed →"**.

That's it — start chatting.

---

## API Endpoints

| Method | Path       | Description                          |
|--------|------------|--------------------------------------|
| POST   | `/ingest`  | Chunk, embed, store documents        |
| POST   | `/chat`    | Stream a RAG-powered answer          |
| GET    | `/chunks`  | Debug: list stored chunks            |
| GET    | `/health`  | Health check                         |

### POST /ingest
```json
{
  "text": "Paste resume or portfolio text here...",
  "source": "resume"
}
```

### POST /chat
```json
{
  "message": "What databases has Sai worked with?",
  "conversation_history": []
}
```
Returns a Server-Sent Events stream of `{ "token": "..." }` objects.

---

## How It Works

### Ingestion pipeline (`ingest.py`)
1. Split text into **400-char chunks with 80-char overlap**
2. Embed all chunks in one OpenAI API call
3. Upsert into `resume_chunks` table with `vector(1536)` column
4. IVFFlat index for fast cosine similarity search

### RAG pipeline (`rag.py`)
1. Embed the user's question
2. Query pgvector: `ORDER BY embedding <=> $1::vector LIMIT 5`
3. Inject top-5 chunks into the LLM context
4. Stream the response back via SSE

### Frontend (`useRAGChat.js`)
- Reads SSE stream with `ReadableStream` API
- Updates React state token-by-token for real-time display
- Keeps last 6 messages as conversation history

---

## Switching to Claude

In `.env`:
```
CHAT_MODEL=claude-3-5-sonnet-20241022
```

Then update `rag.py` to use the Anthropic client:
```python
from anthropic import AsyncAnthropic
client = AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
```

---

## Next Steps (Project 2)

Once this works, extend it:
- **Tool calling** — let the bot fetch your GitHub stars, LinkedIn, live job postings
- **Multi-source RAG** — ingest multiple docs (projects, blog posts, case studies)
- **Evals** — add LangSmith tracing to measure answer quality
- **React Native** — port to mobile with `@anthropic-ai/sdk`

---

## Deployment

**Frontend** → Vercel (just `npm run build` and point Vercel at `/frontend`)

**Backend** → Railway or Render
- Set `DATABASE_URL` to your hosted PostgreSQL (Railway provides this free)
- Set `OPENAI_API_KEY`
- The `pgvector` extension is available on Railway PostgreSQL by default

```bash
# Set VITE_API_URL in frontend before building for production
VITE_API_URL=https://your-backend.railway.app npm run build
```
