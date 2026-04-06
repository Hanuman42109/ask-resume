# Ask My Resume - AI Portfolio Chatbot

> A RAG-powered chatbot that answers recruiter questions about my skills, experience, and projects using real-time semantic search and LLM streaming.

🔗 **[Live Demo](https://your-app.vercel.app)** &nbsp;|&nbsp; ⚙️ **[Backend API](https://your-backend.railway.app/docs)**

---

## What It Does

Instead of sending a static PDF resume, this app lets recruiters and hiring managers **ask natural language questions** and get accurate, context-grounded answers in real time.

```
"Does Sai have production React experience?"
→ Retrieves relevant resume chunks via vector similarity search
→ Streams a grounded answer from Llama 3.3 70B
→ Shows which sources were used
```

---

## Architecture

```
User Question
     │
     ▼
[sentence-transformers]     ← local embedding, no API cost
     │  384-dim vector
     ▼
[pgvector cosine search]    ← top-5 most relevant resume chunks
     │  retrieved context
     ▼
[Groq / Llama 3.3 70B]      ← grounded answer generation
     │  SSE token stream
     ▼
[React frontend]            ← real-time streaming UI
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React 18, Vite, SSE streaming |
| Backend | FastAPI (Python), async/await |
| Vector DB | PostgreSQL + pgvector |
| Embeddings | sentence-transformers `all-MiniLM-L6-v2` (local) |
| LLM | Groq API — Llama 3.3 70B Versatile |
| Deploy | Vercel (frontend) + Railway (backend + DB) |

---

## Features

- **Real-time streaming** — responses stream token by token via Server-Sent Events
- **Source citations** — every answer shows which resume chunks were retrieved
- **Dark / Light / System theme** — persisted in localStorage
- **Live health indicator** — polls backend every 10s, shows real connectivity status
- **Copy button** — one-click copy on every answer
- **Suggested questions** — quick-fire prompts always visible

---

## Run Locally

### Prerequisites
- Docker Desktop
- Python 3.11
- Node.js 18+
- [Groq API key](https://console.groq.com) (free)

### Setup

```bash
# 1. Start PostgreSQL with pgvector
docker compose up -d

# 2. Backend
cd backend
py -3.11 -m venv venv
source venv/Scripts/activate   # Windows
pip install -r requirements.txt
cp .env.example .env           # add your GROQ_API_KEY
uvicorn main:app --reload --port 8000

# 3. Frontend
cd ../frontend
npm install
npm run dev
```

Open **http://localhost:5173**, click **⊕ ingest docs**, paste your resume, start chatting.

---

## Project Structure

```
ask-my-resume/
├── backend/
│   ├── main.py        # FastAPI app, SSE streaming endpoints
│   ├── rag.py         # RAG pipeline: embed → retrieve → stream
│   ├── ingest.py      # Chunking, embedding, pgvector upsert
│   └── requirements.txt
├── frontend/
│   └── src/
│       ├── App.jsx
│       ├── hooks/
│       │   ├── useRAGChat.js      # SSE stream handling
│       │   └── useHealthCheck.js  # Backend health polling
│       └── components/
│           ├── ChatMessage.jsx    # Message + citations + copy
│           ├── ChatInput.jsx      # Input with loading states
│           └── IngestPanel.jsx    # Document ingestion UI
└── docker-compose.yml
```

---

## API Endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/health` | Health check |
| POST | `/ingest` | Chunk, embed, store documents |
| POST | `/chat` | Stream RAG-powered answer |
| GET | `/chunks` | List stored chunks (debug) |

---

## What I Learned Building This

- RAG pipeline design (chunking strategy, overlap, embedding dimensions)
- pgvector cosine similarity search with parameterized queries
- FastAPI async streaming with Server-Sent Events
- React SSE consumption with `ReadableStream` API
- Local embeddings with sentence-transformers (zero API cost)
- Groq API integration (OpenAI-compatible, drop-in swap)

---

## Next Steps

- [ ] Tool calling — fetch live GitHub stats in responses
- [ ] Multi-document RAG — ingest projects, blog posts separately
- [ ] Reranking for better retrieval accuracy
- [ ] React Native mobile version
