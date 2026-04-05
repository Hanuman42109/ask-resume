# Ask My Resume - RAG Portfolio Chatbot

AI-powered chatbot that answers questions about my skills and experience using RAG (Retrieval-Augmented Generation).

## Tech Stack
- **Frontend:** React + Vite + SSE streaming
- **Backend:** FastAPI (Python)
- **Vector DB:** PostgreSQL + pgvector
- **Embeddings:** sentence-transformers (local, free)
- **LLM:** Groq (Llama 3.3 70B)

## Features
- Real-time streaming responses
- Source citations for every answer
- Dark / Light / System theme
- Live backend health indicator

## Run Locally
1. `docker compose up -d`
2. `cd backend && pip install -r requirements.txt && uvicorn main:app --reload`
3. `cd frontend && npm install && npm run dev`
4. Open http://localhost:5173, ingest your resume, start chatting