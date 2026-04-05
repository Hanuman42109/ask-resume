import { useState, useEffect } from "react";

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

export function useHealthCheck() {
  const [status, setStatus] = useState("checking");

  const check = async () => {
    try {
      const res = await fetch(`${API_BASE}/health`, { signal: AbortSignal.timeout(4000) });
      setStatus(res.ok ? "online" : "offline");
    } catch {
      setStatus("offline");
    }
  };

  useEffect(() => {
    check();
    const interval = setInterval(check, 10000);
    return () => clearInterval(interval);
  }, []);

  return status;
}
