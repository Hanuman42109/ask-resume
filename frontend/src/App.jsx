import { useState, useRef, useEffect } from "react";
import ChatMessage from "./components/ChatMessage";
import ChatInput from "./components/ChatInput";
import IngestPanel from "./components/IngestPanel";
import { useRAGChat } from "./hooks/useRAGChat";
import { useHealthCheck } from "./hooks/useHealthCheck";
import "./index.css";

const SUGGESTED_QUESTIONS = [
  "What is Sai's strongest tech stack?",
  "What production experience does he have?",
  "Is he a good fit for an AI startup?",
  "What databases has he worked with?",
  "Tell me about his mobile development experience",
];

const THEMES = ["system", "dark", "light"];
const THEME_ICONS = { system: "⊙", dark: "☾", light: "☀" };
const THEME_LABELS = { system: "system", dark: "dark", light: "light" };

function useTheme() {
  const [theme, setTheme] = useState(() => localStorage.getItem("theme") || "system");

  useEffect(() => {
    const root = document.documentElement;
    const systemDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
    const resolved = theme === "system" ? (systemDark ? "dark" : "light") : theme;
    root.setAttribute("data-theme", resolved);
    localStorage.setItem("theme", theme);
  }, [theme]);

  useEffect(() => {
    const mq = window.matchMedia("(prefers-color-scheme: dark)");
    const handler = () => {
      if (theme === "system")
        document.documentElement.setAttribute("data-theme", mq.matches ? "dark" : "light");
    };
    mq.addEventListener("change", handler);
    return () => mq.removeEventListener("change", handler);
  }, [theme]);

  const cycleTheme = () =>
    setTheme(prev => THEMES[(THEMES.indexOf(prev) + 1) % THEMES.length]);

  return { theme, cycleTheme };
}

const STATUS_CONFIG = {
  checking: { label: "connecting...", cls: "status-dot status-checking" },
  online:   { label: "pgvector · live", cls: "status-dot status-online" },
  offline:  { label: "backend offline", cls: "status-dot status-offline" },
};

export default function App() {
  const { messages, isStreaming, isWaiting, sendMessage, clearMessages } = useRAGChat();
  const [showIngest, setShowIngest] = useState(false);
  const { theme, cycleTheme } = useTheme();
  const backendStatus = useHealthCheck();
  const bottomRef = useRef(null);
  const { label, cls } = STATUS_CONFIG[backendStatus];

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  return (
    <div className="app">
      <header className="header">
        <div className="header-left">
          <div className="logo-mark">
            <span className="logo-bracket">[</span>
            <span className="logo-text">ASK</span>
            <span className="logo-bracket">]</span>
          </div>
          <div className="header-meta">
            <h1>Ask My Resume</h1>
            <span className="header-sub">RAG-powered portfolio assistant</span>
          </div>
        </div>
        <div className="header-right">
          <div className={cls} />
          <span className={`status-label ${backendStatus === "offline" ? "status-label-offline" : ""}`}>{label}</span>
          <button className="btn-ghost btn-theme" onClick={cycleTheme}>
            <span className="theme-icon">{THEME_ICONS[theme]}</span>
            <span className="theme-label">{THEME_LABELS[theme]}</span>
          </button>
          <button className="btn-ghost" onClick={() => setShowIngest(!showIngest)}>
            {showIngest ? "← back to chat" : "⊕ ingest docs"}
          </button>
        </div>
      </header>

      <main className="main">
        {showIngest ? (
          <IngestPanel onSuccess={() => setShowIngest(false)} />
        ) : (
          <>
            <div className="messages">
              {messages.length === 0 ? (
                <div className="empty-state">
                  <div className="empty-ascii">{`┌─────────────────────────────────┐\n│  RAG pipeline ready.            │\n│  Ask anything about Sai.        │\n└─────────────────────────────────┘`}</div>
                  <p className="empty-hint">Try one of these:</p>
                  <div className="suggestions">
                    {SUGGESTED_QUESTIONS.map(q => (
                      <button key={q} className="suggestion-chip" onClick={() => sendMessage(q)}>{q}</button>
                    ))}
                  </div>
                </div>
              ) : (
                messages.map((msg, i) => <ChatMessage key={i} message={msg} />)
              )}
              <div ref={bottomRef} />
            </div>

            {messages.length > 0 && !isStreaming && (
              <div className="suggestions-bar">
                <span className="suggestions-bar-label">suggest:</span>
                <div className="suggestions-bar-chips">
                  {SUGGESTED_QUESTIONS.slice(0, 3).map(q => (
                    <button key={q} className="suggestion-chip suggestion-chip-sm" onClick={() => sendMessage(q)}>{q}</button>
                  ))}
                </div>
              </div>
            )}

            <div className="input-area">
              <ChatInput
                onSend={sendMessage}
                disabled={isStreaming}
                isWaiting={isWaiting}
                onClear={messages.length > 0 ? clearMessages : undefined}
              />
            </div>
          </>
        )}
      </main>
    </div>
  );
}
