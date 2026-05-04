/**
 * useRAGChat
 * Handles streaming SSE from the backend.
 * SSE event types: citations | token | done | error
 */

import { useState, useCallback } from "react";

const API_BASE = import.meta.env.VITE_API_URL || "/api";

export function useRAGChat() {
  const [messages, setMessages] = useState([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [isWaiting, setIsWaiting] = useState(false);

  const sendMessage = useCallback(async (userText) => {
    if (!userText.trim() || isStreaming) return;

    const userMsg = { role: "user", content: userText };
    const newMessages = [...messages, userMsg];
    setMessages(newMessages);
    setIsStreaming(true);
    setIsWaiting(true);

    // Placeholder assistant message
    setMessages([...newMessages, { role: "assistant", content: "", citations: [], loading: true }]);

    try {
      const response = await fetch(`${API_BASE}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: userText,
          conversation_history: messages.slice(-6).map(m => ({
            role: m.role,
            content: m.content,
          })),
        }),
      });

      if (!response.ok) throw new Error(`HTTP ${response.status}`);

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      let fullContent = "";
      let citations = [];

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop(); // keep incomplete line

        for (const line of lines) {
          if (!line.startsWith("data: ")) continue;
          const raw = line.slice(6).trim();
          if (!raw) continue;

          let event;
          try {
            event = JSON.parse(raw);
          } catch (e) {
            console.warn("Failed to parse SSE line:", raw, e);
            continue;
          }

          console.log("SSE event:", event); // debug — visible in browser console

          if (event.type === "citations") {
            citations = event.chunks || [];
            setMessages((prev) => {
              const updated = [...prev];
              updated[updated.length - 1] = {
                role: "assistant",
                content: "",
                citations,
                loading: true,
              };
              return updated;
            });
          }

          else if (event.type === "token") {
            setIsWaiting(false);
            fullContent += event.value;
            setMessages((prev) => {
              const updated = [...prev];
              updated[updated.length - 1] = {
                role: "assistant",
                content: fullContent,
                citations,
                loading: false,
              };
              return updated;
            });
          }

          else if (event.type === "done") {
            break;
          }

          else if (event.type === "error") {
            throw new Error(event.message);
          }
        }
      }
    } catch (err) {
      console.error("Chat error:", err);
      setMessages((prev) => {
        const updated = [...prev];
        updated[updated.length - 1] = {
          role: "assistant",
          content: `Error: ${err.message}`,
          citations: [],
          loading: false,
          isError: true,
        };
        return updated;
      });
    } finally {
      setIsStreaming(false);
      setIsWaiting(false);
    }
  }, [messages, isStreaming]);

  const clearMessages = useCallback(() => setMessages([]), []);

  return { messages, isStreaming, isWaiting, sendMessage, clearMessages };
}
