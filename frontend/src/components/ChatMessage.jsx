import { useState } from "react";

export default function ChatMessage({ message }) {
  const isUser = message.role === "user";
  const [copied, setCopied] = useState(false);
  const [showCitations, setShowCitations] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(message.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className={`message ${isUser ? "message-user" : "message-assistant"} ${message.isError ? "message-error" : ""}`}>
      <div className="message-label-row">
        <span className="message-label">{isUser ? "you >" : "rag >"}</span>
        {!isUser && message.content && !message.loading && (
          <button className="btn-copy" onClick={handleCopy}>
            {copied ? "✓ copied" : "copy"}
          </button>
        )}
      </div>

      <div className="message-content">
        {message.loading && !message.content ? (
          <span className="loading-indicator">
            <span className="loading-dot" />
            <span className="loading-dot" />
            <span className="loading-dot" />
            <span className="loading-text">thinking...</span>
          </span>
        ) : message.content ? (
          message.content
        ) : (
          <span className="cursor-blink">▊</span>
        )}
      </div>

      {!isUser && message.citations && message.citations.length > 0 && (
        <div className="citations">
          <button className="citations-toggle" onClick={() => setShowCitations(!showCitations)}>
            <span>⊞</span>
            {message.citations.length} source{message.citations.length > 1 ? "s" : ""} used
            <span>{showCitations ? "▲" : "▼"}</span>
          </button>
          {showCitations && (
            <div className="citations-list">
              {message.citations.map((c, i) => (
                <div key={i} className="citation-item">
                  <span className="citation-source">{c.source} · chunk {c.chunk_index}</span>
                  <p className="citation-preview">{c.preview}...</p>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
