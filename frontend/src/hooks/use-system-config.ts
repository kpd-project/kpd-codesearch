import { useState, useEffect } from "react";

interface SystemConfig {
  qdrant: { url: string; api_key_masked: string; has_api_key: boolean };
  embeddings: { model: string; dimension: number };
  repos: { base_path: string };
  llm: { base_url: string; api_key_masked: string; has_api_key: boolean };
}

export function useSystemConfig() {
  const [config, setConfig] = useState<SystemConfig | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch("/api/config/system")
      .then((res) => res.json())
      .then((data) => {
        setConfig(data);
        setLoading(false);
      })
      .catch((e) => {
        setError(e.message);
        setLoading(false);
      });
  }, []);

  return { config, loading, error };
}