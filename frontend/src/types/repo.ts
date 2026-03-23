/** Сырые key/value из Qdrant collection metadata (без вычисленных полей карточки). */
export type CollectionMetadata = Record<string, unknown>;

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
  collection_metadata?: CollectionMetadata;
}

/** Прогресс индексации: обработанные файлы относительно общего числа. */
export interface IndexingProgressEntry {
  current: number;
  total: number;
  path: string;
  chunks: number;
  vectors: number;
  skipped: boolean;
}

export interface RepoStatus {
  qdrant: { status: string; connected: boolean };
  repos: Repo[];
  settings: Settings;
  indexing_progress: Record<string, IndexingProgressEntry>;
  uptime: string;
}

export interface Settings {
  model: string;
  temperature: number;
  top_k: number;
  max_chunks: number;
}

export type RepoStatusType = "ready" | "indexing" | "error";

/** Папка под REPOS_BASE_PATH для диалога добавления репозитория. */
export interface RepoFolderCandidate {
  folder: string;
  relative_path: string;
  already_added: boolean;
  collection_name: string | null;
}

/** Причина пропуска файла чанкером. */
export type SkipReason =
  | 'ignored_directory'
  | 'ignored_name'
  | 'ignored_extension'
  | 'gitignore'
  | 'unsupported_extension'
  | 'node_modules_path';

/** Узел дерева файлов репозитория (ответ GET /api/repos/{name}/file-tree). */
export interface FileTreeNode {
  type: 'file' | 'dir';
  name: string;
  /** Относительный POSIX-путь от корня репозитория. */
  path: string;
  /** Только для file, с точкой, нижний регистр (.tsx). null если нет суффикса. */
  extension: string | null;
  /** true = войдёт в индекс; false = пропускается; null = обычная папка. */
  indexed: boolean | null;
  skip_reason: SkipReason | null;
  /** Для dir — дочерние узлы; у IGNORE_DIRS-заглушки []; у file null. */
  children: FileTreeNode[] | null;
}

export interface FileTreeResponse {
  tree: FileTreeNode[];
  meta: {
    repo: string;
    root_path: string;
    generated_at: string;
    indexed_file_count: number;
    skipped_file_count: number;
  };
}
