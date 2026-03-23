import { useState, useEffect, useCallback } from 'react';
import { useStatus } from '@/hooks/use-api';
import { useLocalStorage } from '@/hooks/use-local-storage';
import { apiUrl } from '@/lib/api-url';
import { RepoFileTree, type FileTreeFilter } from '@/components/repo/repo-file-tree';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { ChevronDown, ChevronUp } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { FileTreeNode, FileTreeResponse } from '@/types/repo';

const STORAGE_KEY = 'kpd-codesearch-chunk-file-test-v1';

interface StoredPrefs {
    repo: string;
    filter: FileTreeFilter;
}

const DEFAULT_PREFS: StoredPrefs = { repo: '', filter: 'all' };

function deserializePrefs(raw: string | undefined): StoredPrefs {
    if (!raw) return DEFAULT_PREFS;
    try {
        const p = JSON.parse(raw) as Record<string, unknown>;
        return {
            repo: typeof p.repo === 'string' ? p.repo : DEFAULT_PREFS.repo,
            filter:
                p.filter === 'all' || p.filter === 'indexed' || p.filter === 'skipped'
                    ? p.filter
                    : DEFAULT_PREFS.filter,
        };
    } catch {
        return DEFAULT_PREFS;
    }
}

interface ChunkResult {
    content: string;
    metadata: {
        repo: string;
        path: string;
        language: string;
        type: string;
        name?: string;
    };
}

function ChunkCard({ chunk, index }: { chunk: ChunkResult; index: number }) {
    const [expanded, setExpanded] = useState(index === 0);

    const onToggleHandler = () => setExpanded((v) => !v);

    return (
        <div className="border border-border rounded-lg bg-card text-card-foreground">
            <div
                className="flex items-center gap-3 px-4 py-2.5 cursor-pointer select-none"
                onClick={onToggleHandler}
            >
                <span className="font-mono text-xs text-muted-foreground shrink-0">#{index + 1}</span>
                <div className="flex flex-wrap items-center gap-1.5 flex-1 min-w-0">
                    {chunk.metadata.name && (
                        <Badge variant="outline" className="font-mono text-xs shrink-0">
                            {chunk.metadata.name}
                        </Badge>
                    )}
                    {chunk.metadata.type && (
                        <span className="text-xs text-muted-foreground">{chunk.metadata.type}</span>
                    )}
                    {chunk.metadata.language && (
                        <span className="text-xs text-muted-foreground">{chunk.metadata.language}</span>
                    )}
                </div>
                <span className="shrink-0 text-muted-foreground">
                    {expanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                </span>
            </div>
            {expanded && (
                <div className="border-t border-border px-4 py-3">
                    <pre className="font-mono text-xs whitespace-pre-wrap wrap-break-word leading-relaxed text-foreground/90 max-h-80 overflow-y-auto">
                        {chunk.content}
                    </pre>
                </div>
            )}
        </div>
    );
}

const FILTER_OPTIONS: { value: FileTreeFilter; label: string }[] = [
    { value: 'all', label: 'Все' },
    { value: 'indexed', label: 'В индексе' },
    { value: 'skipped', label: 'Пропущены' },
];

export function ChunkFileTest() {
    const { status } = useStatus();
    const repos = status?.repos ?? [];

    const [prefs, setPrefs] = useLocalStorage<StoredPrefs>({
        key: STORAGE_KEY,
        defaultValue: DEFAULT_PREFS,
        deserialize: deserializePrefs,
        getInitialValueInEffect: false,
    });

    const { repo, filter } = prefs;

    // Сбрасываем репо если он пропал из списка
    useEffect(() => {
        if (!repo) return;
        const exists = repos.some((r) => r.name === repo);
        if (repos.length > 0 && !exists) setPrefs((p) => ({ ...p, repo: '' }));
    }, [repos, repo, setPrefs]);

    const [treeLoading, setTreeLoading] = useState(false);
    const [treeError, setTreeError] = useState<string | null>(null);
    const [treeData, setTreeData] = useState<FileTreeResponse | null>(null);

    const [selectedPath, setSelectedPath] = useState<string | null>(null);
    const [chunksLoading, setChunksLoading] = useState(false);
    const [chunksError, setChunksError] = useState<string | null>(null);
    const [chunks, setChunks] = useState<ChunkResult[] | null>(null);
    const [chunkedPath, setChunkedPath] = useState<string | null>(null);

    const loadTree = useCallback(async (repoName: string) => {
        setTreeLoading(true);
        setTreeError(null);
        setTreeData(null);
        setSelectedPath(null);
        setChunks(null);
        setChunkedPath(null);
        try {
            const res = await fetch(apiUrl(`/api/repos/${encodeURIComponent(repoName)}/file-tree`));
            if (!res.ok) {
                const data = await res.json().catch(() => ({}));
                throw new Error(data?.detail ?? `HTTP ${res.status}`);
            }
            setTreeData(await res.json());
        } catch (e) {
            setTreeError(e instanceof Error ? e.message : 'Ошибка загрузки');
        } finally {
            setTreeLoading(false);
        }
    }, []);

    // Загружаем дерево при смене репо
    useEffect(() => {
        if (!repo) return;
        void loadTree(repo);
    }, [repo, loadTree]);

    const onRepoChangeHandler = (value: string | null) => {
        if (value) setPrefs((p) => ({ ...p, repo: value }));
    };

    const onFilterChangeHandler = (value: FileTreeFilter) => {
        setPrefs((p) => ({ ...p, filter: value }));
    };

    const onFileSelectHandler = useCallback(
        async (path: string, node: FileTreeNode) => {
            if (!node.indexed || !repo) return;
            setSelectedPath(path);
            if (path === chunkedPath) return; // уже загружено
            setChunksLoading(true);
            setChunksError(null);
            setChunks(null);
            try {
                const res = await fetch(
                    apiUrl(`/api/repos/${encodeURIComponent(repo)}/chunk-preview`),
                    {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ path }),
                    },
                );
                if (!res.ok) {
                    const data = await res.json().catch(() => ({}));
                    throw new Error(data?.detail ?? `HTTP ${res.status}`);
                }
                const data = await res.json();
                setChunks(data.chunks);
                setChunkedPath(path);
            } catch (e) {
                setChunksError(e instanceof Error ? e.message : 'Ошибка загрузки чанков');
            } finally {
                setChunksLoading(false);
            }
        },
        [repo, chunkedPath],
    );

    const treeNodes = treeData?.tree ?? [];
    const meta = treeData?.meta;

    return (
        <div className="h-full flex flex-col">
            {/* Toolbar */}
            <div className="shrink-0 border-b border-border bg-background px-4 py-2.5 flex flex-wrap items-center gap-3">
                <Select value={repo} onValueChange={onRepoChangeHandler}>
                    <SelectTrigger className="w-48 h-8 text-sm">
                        <SelectValue placeholder="Выберите репозиторий" />
                    </SelectTrigger>
                    <SelectContent>
                        {repos.map((r) => (
                            <SelectItem key={r.name} value={r.name}>
                                {r.name}
                            </SelectItem>
                        ))}
                    </SelectContent>
                </Select>

                <div className="flex items-center gap-1 rounded-md border border-border p-0.5 bg-muted/30">
                    {FILTER_OPTIONS.map((opt) => (
                        <button
                            key={opt.value}
                            type="button"
                            onClick={() => onFilterChangeHandler(opt.value)}
                            className={cn(
                                'px-2.5 py-1 rounded text-xs font-medium transition-colors',
                                filter === opt.value
                                    ? 'bg-background text-foreground shadow-sm'
                                    : 'text-muted-foreground hover:text-foreground',
                            )}
                        >
                            {opt.label}
                        </button>
                    ))}
                </div>

                {meta && (
                    <div className="flex items-center gap-2 text-xs text-muted-foreground ml-auto">
                        <span className="text-emerald-600 dark:text-emerald-400">
                            ↑ {meta.indexed_file_count} в индексе
                        </span>
                        <span className="text-muted-foreground/50">·</span>
                        <span>{meta.skipped_file_count} пропущено</span>
                    </div>
                )}
            </div>

            {/* Split: дерево слева, чанки справа */}
            <div className="flex-1 flex min-h-0 overflow-hidden">
                {/* Левая панель — дерево */}
                <div className="w-72 shrink-0 border-r border-border flex flex-col min-h-0">
                    <ScrollArea className="flex-1 min-h-0">
                        {!repo && (
                            <div className="py-12 text-center text-muted-foreground text-xs px-4">
                                Выберите репозиторий
                            </div>
                        )}
                        {repo && treeLoading && (
                            <div className="py-12 text-center text-muted-foreground text-xs">Загрузка…</div>
                        )}
                        {repo && treeError && (
                            <div className="m-3 rounded border border-destructive/50 bg-destructive/10 px-3 py-2 text-xs text-destructive">
                                {treeError}
                            </div>
                        )}
                        {!treeLoading && !treeError && treeNodes.length > 0 && (
                            <RepoFileTree
                                nodes={treeNodes}
                                selected={selectedPath}
                                onSelect={onFileSelectHandler}
                                filter={filter}
                            />
                        )}
                    </ScrollArea>
                </div>

                {/* Правая панель — чанки */}
                <ScrollArea className="flex-1 min-h-0">
                    <div className="p-4 space-y-3">
                        {!selectedPath && !chunksLoading && (
                            <div className="py-16 text-center text-muted-foreground text-sm">
                                Выберите файл из дерева слева
                            </div>
                        )}

                        {chunksLoading && (
                            <div className="py-16 text-center text-muted-foreground text-sm">
                                Чанкинг…
                            </div>
                        )}

                        {chunksError && (
                            <div className="rounded border border-destructive/50 bg-destructive/10 px-4 py-3 text-sm text-destructive">
                                {chunksError}
                            </div>
                        )}

                        {chunks && !chunksLoading && (
                            <>
                                <div className="flex items-center justify-between text-xs text-muted-foreground px-0.5">
                                    <span className="font-mono truncate text-foreground/70">
                                        {chunkedPath}
                                    </span>
                                    <span className="shrink-0 ml-3">
                                        {chunks.length} чанк{chunks.length === 1 ? '' : chunks.length < 5 ? 'а' : 'ов'}
                                    </span>
                                </div>
                                {chunks.length === 0 ? (
                                    <div className="py-8 text-center text-muted-foreground text-sm">
                                        Чанков нет
                                    </div>
                                ) : (
                                    chunks.map((chunk, i) => (
                                        <ChunkCard key={i} chunk={chunk} index={i} />
                                    ))
                                )}
                            </>
                        )}
                    </div>
                </ScrollArea>
            </div>
        </div>
    );
}
