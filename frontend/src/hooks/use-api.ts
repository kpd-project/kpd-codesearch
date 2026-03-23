import {
  createContext,
  createElement,
  useContext,
  useState,
  useEffect,
  useCallback,
  useMemo,
  useRef,
  type ReactNode,
} from "react";
import type { IndexingProgressEntry } from "@/types/repo";

interface Status {
  qdrant: { status: string; connected: boolean };
  repos: Repo[];
  settings: Settings;
  indexing_progress: Record<string, IndexingProgressEntry>;
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
  /** Режим RAG (runtime). */
  rag_mode?: "simple" | "agent";
}

type WsMessage = Record<string, unknown> & { _seq?: number };

function useWebSocket() {
  const [connected, setConnected] = useState(false);
  const [messages, setMessages] = useState<WsMessage[]>([]);
  const [ws, setWs] = useState<WebSocket | null>(null);
  const seqRef = useRef(0);

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
          const data = JSON.parse(event.data) as Record<string, unknown>;
          const seq = ++seqRef.current;
          setMessages((prev) => [...prev.slice(-50), { ...data, _seq: seq }]);
        } catch {
          console.error("Failed to parse WebSocket message");
        }
      };

      socket.onerror = (e) => {
        console.error("WebSocket error", e);
      };

      socket.onclose = () => {
        setConnected(false);
        if (cancelled) return;

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

function useStatusState() {
  const [status, setStatus] = useState<Status | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const { connected, messages } = useWebSocket();
  const lastHandledSeq = useRef(0);
  const [liveProgress, setLiveProgress] = useState<
    Record<string, IndexingProgressEntry>
  >({});

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

  useEffect(() => {
    for (const raw of messages) {
      const seq = raw._seq ?? 0;
      if (seq <= lastHandledSeq.current) continue;
      lastHandledSeq.current = seq;

      const type = raw.type;
      if (type === "index_start" && typeof raw.repo === "string") {
        const repoName = raw.repo;
        setLiveProgress((prev) => {
          const n = { ...prev };
          delete n[repoName];
          return n;
        });
      }
      if (
        type === "index_progress" &&
        typeof raw.repo === "string" &&
        raw.progress
      ) {
        const repoName = raw.repo;
        setLiveProgress((prev) => ({
          ...prev,
          [repoName]: raw.progress as IndexingProgressEntry,
        }));
      }
      if (
        (type === "index_complete" || type === "index_error") &&
        typeof raw.repo === "string"
      ) {
        const repoName = raw.repo;
        setLiveProgress((prev) => {
          const n = { ...prev };
          delete n[repoName];
          return n;
        });
        void fetchStatus();
      }
      if (type === "settings_updated") {
        void fetchStatus();
      }
    }
  }, [messages, fetchStatus]);

  const mergedStatus = useMemo(() => {
    if (!status) return null;
    return {
      ...status,
      indexing_progress: {
        ...status.indexing_progress,
        ...liveProgress,
      },
    };
  }, [status, liveProgress]);

  return {
    status: mergedStatus,
    loading,
    error,
    refetch: fetchStatus,
    wsConnected: connected,
  };
}

export type StatusContextValue = ReturnType<typeof useStatusState>;

const StatusContext = createContext<StatusContextValue | null>(null);

/** Один экземпляр WS + опрос /api/status на всё приложение. */
export function StatusProvider({ children }: { children: ReactNode }) {
  const value = useStatusState();
  return createElement(StatusContext.Provider, { value }, children);
}

export function useStatus(): StatusContextValue {
  const ctx = useContext(StatusContext);
  if (!ctx) {
    throw new Error("useStatus must be used within StatusProvider");
  }
  return ctx;
}
