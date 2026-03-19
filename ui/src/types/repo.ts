export interface Repo {
  name: string;
  display_name?: string | null;
  path: string;
  relative_path?: string | null;
  indexed_path?: string | null;
  enabled: boolean;
  chunks: number;
  last_indexed: string | null;
  status: string;
  description?: string | null;
  short_description?: string | null;
  embedder_model?: string | null;
  embedder_dimension?: number | null;
}

export interface RepoStatus {
  qdrant: { status: string; connected: boolean };
  repos: Repo[];
  settings: Settings;
  indexing_progress: Record<string, number>;
  uptime: string;
}

export interface Settings {
  model: string;
  temperature: number;
  top_k: number;
  max_chunks: number;
}

export type RepoStatusType = "ready" | "indexing" | "error";
