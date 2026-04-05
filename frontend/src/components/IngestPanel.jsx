import { useState } from "react";

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

export default function IngestPanel({ onSuccess }) {
  const [text, setText] = useState("");
  const [source, setSource] = useState("resume");
  const [status, setStatus] = useState(null);
  const [message, setMessage] = useState("");

  const handleIngest = async () => {
    if (!text.trim()) return;
    setStatus("loading");
    setMessage("");
    try {
      const res = await fetch(`${API_BASE}/ingest`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text, source }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Ingest failed");
      setStatus("success");
      setMessage(data.message);
      setTimeout(() => onSuccess?.(), 1500);
    } catch (err) {
      setStatus("error");
      setMessage(err.message);
    }
  };

  return (
    <div className="ingest-panel">
      <div className="ingest-header">
        <h2>Ingest Documents</h2>
        <p>Paste your resume or portfolio text. It will be chunked, embedded, and stored in pgvector.</p>
      </div>

      <div className="ingest-field">
        <label>Source label</label>
        <input className="ingest-source-input" value={source} onChange={(e) => setSource(e.target.value)} placeholder="resume" />
      </div>

      <div className="ingest-field">
        <label>Document text</label>
        <textarea
          className="ingest-textarea"
          value={text}
          onChange={(e) => setText(e.target.value)}
          rows={18}
          placeholder="Paste your resume, project descriptions, bio..."
        />
        <span className="char-count">{text.length} chars · ~{Math.ceil(text.length / 400)} chunks estimated</span>
      </div>

      {message && (
        <div className={`ingest-status ${status}`}>
          {status === "loading" ? "⟳ Processing..." : status === "success" ? `✓ ${message}` : `✗ ${message}`}
        </div>
      )}

      <button className="btn-ingest" onClick={handleIngest} disabled={status === "loading" || !text.trim()}>
        {status === "loading" ? "Embedding chunks..." : "Ingest & embed →"}
      </button>
    </div>
  );
}
