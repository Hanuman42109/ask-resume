# Ask My Resume - RAG Portfolio Chatbot

A deployed RAG application that lets visitors chat with Sai's resume and portfolio content.
The app uses a React frontend, a FastAPI backend, Nomic embeddings, pgvector retrieval, and streamed chat responses.

## Live App

- Frontend: [ask-resume-cs.vercel.app](https://ask-resume-cs.vercel.app/)
- Backend: Render FastAPI service, configured in Vercel with `VITE_API_URL`
- Keep-alive: [cron-job.org](https://cron-job.org/) pings the Render `/health` endpoint so the free Render service wakes up before visitors hit the chat flow

```text
User question
     |
     v
Embed question with Nomic
     |
     v
pgvector cosine search
     |
     v
Top-K relevant resume chunks
     |
     v
Groq chat completion
     |
     v
Streamed answer in React UI
```

## Stack

| Layer      | Tech                                      |
|------------|-------------------------------------------|
| Frontend   | React + Vite + SSE streaming              |
| Backend    | FastAPI (Python)                          |
| Vector DB  | PostgreSQL + pgvector                     |
| Embeddings | Nomic `nomic-embed-text-v1.5`             |
| LLM        | Groq Chat Completions via OpenAI SDK      |
| Deploy     | Vercel frontend + Render backend          |
| Wake-up    | cron-job.org scheduled `/health` request  |

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
# Edit .env with DATABASE_URL, NOMIC_API_KEY, and GROQ_API_KEY

uvicorn main:app --reload --port 8000
```

If you previously created older folders such as `venv/` or `.venv/`, you can remove them to avoid confusion.

### 3. Frontend setup

```bash
cd frontend
npm install
npm run dev
# http://localhost:5173
```

For local development, set `VITE_API_URL=http://localhost:8000` if the frontend should call the local FastAPI backend directly.

### 4. Ingest resume content

Open the app, click **"+ ingest docs"**, paste resume or portfolio text, then click **"Ingest & embed ->"**.

The backend chunks the content, creates Nomic embeddings, and stores the vectors in PostgreSQL.

## API Endpoints

| Method | Path      | Description                   |
|--------|-----------|-------------------------------|
| GET    | `/health` | Health check for Render/cron  |
| POST   | `/ingest` | Chunk, embed, store documents |
| POST   | `/chat`   | Stream a RAG-powered answer   |
| GET    | `/chunks` | Debug: list stored chunks     |

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

Returns a Server-Sent Events stream with citation, token, done, or error events.

## How It Works

### Ingestion pipeline (`backend/ingest.py`)

1. Split text into 400-character chunks with 80-character overlap.
2. Embed chunks with Nomic `nomic-embed-text-v1.5` using `task_type="search_document"`.
3. Store chunks in the `resume_chunks` table with a `vector(768)` embedding column.
4. Use pgvector for similarity search during chat.

### RAG pipeline (`backend/rag.py`)

1. Embed the user's question with Nomic using `task_type="search_query"`.
2. Query pgvector with `ORDER BY embedding <=> $1::vector LIMIT 5`.
3. Send the top chunks as context to the configured Groq chat model.
4. Stream the response back to the frontend with SSE.

### Frontend (`frontend/src/hooks/useRAGChat.js`)

- Calls the backend `/chat` endpoint.
- Reads the SSE stream with the `ReadableStream` API.
- Displays citations and token-by-token responses in the React UI.
- Keeps recent messages as conversation history.

## Deployment Notes

### Vercel frontend

Set the frontend environment variable:

```text
VITE_API_URL=https://your-render-service.onrender.com
```

### Render backend

Set the backend environment variables:

```text
DATABASE_URL=postgresql://...
NOMIC_API_KEY=...
GROQ_API_KEY=...
CHAT_MODEL=llama-3.3-70b-versatile
```

Render free services can sleep after inactivity, so this deployment uses cron-job.org to call:

```text
https://your-render-service.onrender.com/health
```

A 10- to 14-minute interval keeps the service warm before Render's idle timeout.
