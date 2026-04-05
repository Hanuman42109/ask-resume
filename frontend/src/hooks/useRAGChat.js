import { useState, useCallback } from "react";

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

export function useRAGChat() {
  const [messages, setMessages] = useState([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [isWaiting, setIsWaiting] = useState(false);

  const sendMessage = useCallback(async (userText) => {
    if (!userText.trim() || isStreaming) return;

    const userMsg = { role: "user", content: userText };
    const history = messages.slice(-6).map(m => ({ role: m.role, content: m.content }));
    const newMessages = [...messages, userMsg];

    setMessages([...newMessages, { role: "assistant", content: "", citations: [], loading: true }]);
    setIsStreaming(true);
    setIsWaiting(true);

    try {
      const res = await fetch(`${API_BASE}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: userText, conversation_history: history }),
      });

      if (!res.ok) throw new Error(`HTTP ${res.status}`);

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buf = "";
      let fullContent = "";
      let citations = [];

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buf += decoder.decode(value, { stream: true });
        const lines = buf.split("\n");
        buf = lines.pop();

        for (const line of lines) {
          if (!line.startsWith("data: ")) continue;
          const raw = line.slice(6).trim();
          if (!raw) continue;

          let event;
          try { event = JSON.parse(raw); }
          catch { continue; }

          if (event.type === "citations") {
            citations = event.chunks || [];
            setMessages(prev => {
              const u = [...prev];
              u[u.length - 1] = { role: "assistant", content: "", citations, loading: true };
              return u;
            });
          }

          else if (event.type === "token") {
            setIsWaiting(false);
            fullContent += event.value;
            setMessages(prev => {
              const u = [...prev];
              u[u.length - 1] = { role: "assistant", content: fullContent, citations, loading: false };
              return u;
            });
          }

          else if (event.type === "error") {
            throw new Error(event.message);
          }
        }
      }
    } catch (err) {
      setMessages(prev => {
        const u = [...prev];
        u[u.length - 1] = { role: "assistant", content: `Error: ${err.message}`, citations: [], loading: false, isError: true };
        return u;
      });
    } finally {
      setIsStreaming(false);
      setIsWaiting(false);
    }
  }, [messages, isStreaming]);

  const clearMessages = useCallback(() => setMessages([]), []);
  return { messages, isStreaming, isWaiting, sendMessage, clearMessages };
}
