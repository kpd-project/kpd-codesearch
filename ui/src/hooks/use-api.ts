import { useState, useEffect, useCallback } from "react";

interface Status {
  qdrant: { status: string; connected: boolean };
  repos: Repo[];
  settings: Settings;
  indexing_progress: Record<string, number>;
  uptime: string;
}

interface Repo {
  name: string;
  path: string;
  enabled: boolean;
  chunks: number;
  last_indexed: string | null;
  status: string;
  description?: string | null;
}

interface Settings {
  model: string;
  temperature: number;
  top_k: number;
  max_chunks: number;
}

export function useStatus() {
  const [status, setStatus] = useState<Status | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchStatus = useCallback(async () => {
    try {
      const res = await fetch("/api/status");
      if (!res.ok) throw new Error("Failed to fetch status");
      const data = await res.json();
      setStatus(data);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unknown error");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchStatus();
    const interval = setInterval(fetchStatus, 5000);
    return () => clearInterval(interval);
  }, [fetchStatus]);

  return { status, loading, error, refetch: fetchStatus };
}

export function useWebSocket() {
  const [connected, setConnected] = useState(false);
  const [messages, setMessages] = useState<Record<string, unknown>[]>([]);
  const [ws, setWs] = useState<WebSocket | null>(null);

  useEffect(() => {
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const wsUrl = `${protocol}//${window.location.host}/ws/state`;

    let socket: WebSocket | null = null;
    let cancelled = false;
    let retry = 0;
    let reconnectTimeoutId: number | undefined;

    const connect = () => {
      if (cancelled) return;

      socket = new WebSocket(wsUrl);
      setWs(socket);

      socket.onopen = () => {
        setConnected(true);
        retry = 0;
        console.log("WebSocket connected");
      };

      socket.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          setMessages((prev) => [...prev.slice(-50), data]);
        } catch {
          console.error("Failed to parse WebSocket message");
        }
      };

      socket.onerror = (e) => {
        // В некоторых браузерах причину можно увидеть только в консоли,
        // поэтому пишем хоть что-то.
        console.error("WebSocket error", e);
      };

      socket.onclose = () => {
        setConnected(false);
        if (cancelled) return;

        // Экспоненциальная задержка до максимума — чтобы не спамить сервер.
        const baseDelay = 300;
        const delay =
          Math.min(5000, baseDelay * Math.pow(2, retry)) + Math.random() * 200;
        retry += 1;

        reconnectTimeoutId = window.setTimeout(connect, delay);
      };
    };

    connect();

    return () => {
      cancelled = true;
      if (reconnectTimeoutId) window.clearTimeout(reconnectTimeoutId);
      try {
        socket?.close();
      } catch {
        // noop
      }
    };
  }, []);

  return { connected, messages, ws };
}

export function useRepos() {
  const { status, refetch } = useStatus();
  return {
    repos: status?.repos || [],
    refetch,
  };
}
