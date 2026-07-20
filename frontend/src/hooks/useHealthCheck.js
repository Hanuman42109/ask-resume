/**
 * useHealthCheck
 * Polls the backend /health endpoint every 10 seconds.
 * Returns: "checking" | "online" | "offline"
 */

import { useState, useEffect } from "react";

const API_BASE = import.meta.env.VITE_API_URL || "/api";
const POLL_INTERVAL = 10000; // 10 seconds

export function useHealthCheck() {
  const [status, setStatus] = useState("checking"); // checking | online | offline

  const check = async () => {
    try {
      const res = await fetch(`${API_BASE}/health`, {
        signal: AbortSignal.timeout(4000), // 4s timeout
      });
      setStatus(res.ok ? "online" : "offline");
    } catch {
      setStatus("offline");
    }
  };

  useEffect(() => {
    check(); // run immediately on mount
    const interval = setInterval(check, POLL_INTERVAL);
    return () => clearInterval(interval);
  }, []);

  return status;
}
