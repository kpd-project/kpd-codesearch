import { useState, useEffect } from 'react';
import { useStatus } from '@/hooks/use-api';
import { useLocalStorage } from '@/hooks/use-local-storage';
import { apiUrl } from '@/lib/api-url';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { Switch } from '@/components/ui/switch';
import { Search, ChevronDown, ChevronUp, X } from 'lucide-react';
import { cn } from '@/lib/utils';

interface ChunkResult {
    id: string;
    score: number;
    repo: string;
    path: string;
    language: string;
    type: string;
    name: string;
    content: string;
}

interface SearchMeta {
    query: string;
    repo: string | null;
    top_k: number;
    min_score: number | null;
    total: number;
    search_all_limit: number | null;
}

interface SearchResponse {
    chunks: ChunkResult[];
    meta: SearchMeta;
}

const VECTOR_SEARCH_TEST_STORAGE_KEY = 'kpd-codesearch-vector-search-test-v1';

/** Стабильная ссылка на пустой список, пока нет status (не триггерим лишние эффекты). */
const EMPTY_REPO_LIST: { name: string }[] = [];

interface VectorSearchStored {
    query: string;
    repo: string;
    top_k: number;
    min_score: number;
    use_min_score: boolean;
}

const DEFAULT_VECTOR_SEARCH: VectorSearchStored = {
    query: '',
    repo: '__all__',
    top_k: 5,
    min_score: 0.5,
    use_min_score: true,
};

function deserializeVectorSearchPrefs(raw: string | undefined): VectorSearchStored {
    const d = DEFAULT_VECTOR_SEARCH;
    if (raw == null || raw === '') return d;
    try {
        const p = JSON.parse(raw) as Record<string, unknown>;
        return {
            query: typeof p.query === 'string' ? p.query : d.query,
            repo: typeof p.repo === 'string' ? p.repo : d.repo,
            top_k:
                typeof p.top_k === 'number' && Number.isFinite(p.top_k)
                    ? Math.min(15, Math.max(1, Math.round(p.top_k)))
                    : d.top_k,
            min_score:
                typeof p.min_score === 'number' && Number.isFinite(p.min_score)
                    ? Math.min(1, Math.max(0, p.min_score))
                    : d.min_score,
            use_min_score: typeof p.use_min_score === 'boolean' ? p.use_min_score : d.use_min_score,
        };
    } catch {
        return d;
    }
}

function splitFilePath(path: string): { dir: string; base: string } {
    const i = Math.max(path.lastIndexOf('/'), path.lastIndexOf('\\'));
    if (i < 0) return { dir: '', base: path };
    return { dir: path.slice(0, i + 1), base: path.slice(i + 1) };
}

function ChunkCard({ chunk }: { chunk: ChunkResult }) {
    const [expanded, setExpanded] = useState(false);

    const { dir, base } = splitFilePath(chunk.path);

    return (
        <div className="border border-border rounded-lg bg-card text-card-foreground">
            {/* Header */}
            <div
                className="flex items-center gap-3 px-4 py-3 cursor-pointer select-none"
                onClick={() => setExpanded((v) => !v)}
            >
                {/* score 0–1: ≥0.7 / 0.5–0.7 / 0.35–0.5 / ниже 0.35 */}
                <div
                    className={cn(
                        'mt-0.5 shrink-0 border border-border rounded-2xl font-mono text-xs px-2 py-0.5 -mt-0.2',
                        chunk.score >= 0.7 && 'bg-emerald-500/15 text-emerald-800 dark:text-emerald-400',
                        chunk.score >= 0.5 && chunk.score < 0.7 && 'bg-amber-500/15 text-amber-800 dark:text-amber-400',
                        chunk.score >= 0.35 &&
                            chunk.score < 0.5 &&
                            'bg-orange-500/15 text-orange-800 dark:text-orange-400',
                        chunk.score < 0.35 && 'bg-red-500/15 text-red-600 dark:text-red-400',
                    )}
                >
                    {chunk.score.toFixed(3)}
                </div>
                <div className="flex-1 min-w-0">
                    <div className="flex flex-wrap items-center gap-1.5 mb-0.5 min-w-0">
                        <span className="font-mono text-sm block min-w-0 truncate">
                            {dir && <span className="text-muted-foreground">{dir}</span>}
                            <span className="text-foreground">{base}</span>
                        </span>
                        {chunk.name && (
                            <Badge variant="outline" className="text-xs font-mono shrink-0">
                                {chunk.name}
                            </Badge>
                        )}
                    </div>
                </div>
                <div className="flex flex-wrap gap-1.5 text-xs text-muted-foreground">
                    <span>{chunk.repo}</span>
                    {chunk.language && <span>&bull; {chunk.language}</span>}
                    {chunk.type && <span>&bull; {chunk.type}</span>}
                    <span className="ml-auto font-mono opacity-60">&bull; {chunk.id.slice(0, 8)}…</span>
                </div>
                <span className="shrink-0 text-muted-foreground">
                    {expanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                </span>
            </div>

            {/* Content */}
            {expanded && (
                <div className="border-t border-border px-4 py-3">
                    <pre className="font-mono  whitespace-pre-wrap wrap-break-word leading-relaxed text-foreground/90 max-h-96 overflow-y-auto">
                        {chunk.content}
                    </pre>
                </div>
            )}
        </div>
    );
}

export function VectorSearchTest() {
    const { status } = useStatus();
    const repos = status?.repos ?? EMPTY_REPO_LIST;

    const [prefs, setPrefs] = useLocalStorage<VectorSearchStored>({
        key: VECTOR_SEARCH_TEST_STORAGE_KEY,
        defaultValue: DEFAULT_VECTOR_SEARCH,
        deserialize: deserializeVectorSearchPrefs,
        getInitialValueInEffect: false,
    });

    const { query, repo, top_k: topK, min_score: minScore, use_min_score: useMinScore } = prefs;

    /** Если сохранённый репозиторий пропал из списка — сбрасываем на «все». */
    useEffect(() => {
        if (repo === '__all__') return;
        const exists = repos.some((r) => r.name === repo);
        if (repos.length > 0 && !exists) setPrefs((p) => ({ ...p, repo: '__all__' }));
    }, [repos, repo, setPrefs]);

    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [result, setResult] = useState<SearchResponse | null>(null);

    const handleSearch = async () => {
        if (!query.trim()) return;
        setLoading(true);
        setError(null);
        setResult(null);
        try {
            const res = await fetch(apiUrl('/api/tests/vector-search'), {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    query: query.trim(),
                    repo: repo === '__all__' ? null : repo,
                    top_k: topK,
                    min_score: useMinScore ? minScore : null,
                }),
            });
            if (!res.ok) {
                const data = await res.json().catch(() => ({}));
                throw new Error(data?.detail ?? `HTTP ${res.status}`);
            }
            setResult(await res.json());
        } catch (e) {
            setError(e instanceof Error ? e.message : 'Неизвестная ошибка');
        } finally {
            setLoading(false);
        }
    };

    const handleKeyDown = (e: React.KeyboardEvent) => {
        if (e.key === 'Enter' && !e.shiftKey) handleSearch();
    };

    return (
        <div className="h-full flex flex-col">
            {/* Search Form */}
            <div className="shrink-0 border-b border-border bg-background p-4 space-y-4">
                <div className="flex gap-2">
                    <div className="relative flex-1">
                        <Input
                            placeholder="Поисковый запрос…"
                            value={query}
                            onChange={(e) => setPrefs((p) => ({ ...p, query: e.target.value }))}
                            onKeyDown={handleKeyDown}
                            className="w-full pr-9 font-mono text-sm"
                        />
                        {query.length > 0 && (
                            <Button
                                type="button"
                                variant="ghost"
                                size="icon"
                                className="absolute right-0.5 top-1/2 h-7 w-7 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                                onClick={() => setPrefs((p) => ({ ...p, query: '' }))}
                                title="Очистить запрос"
                                aria-label="Очистить запрос"
                            >
                                <X className="h-4 w-4" />
                            </Button>
                        )}
                    </div>
                    <Button onClick={handleSearch} disabled={loading || !query.trim()}>
                        <Search className="w-4 h-4 mr-1.5" />
                        Искать
                    </Button>
                </div>

                <div className="flex flex-wrap items-center gap-4">
                    {/* Repo selector */}
                    <div className="flex items-center gap-2">
                        <Label className="text-sm text-muted-foreground whitespace-nowrap">Репозиторий</Label>
                        <Select value={repo} onValueChange={(v) => v != null && setPrefs((p) => ({ ...p, repo: v }))}>
                            <SelectTrigger className="w-48 h-8 text-sm">
                                <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                                <SelectItem value="__all__">Все репозитории</SelectItem>
                                {repos.map((r) => (
                                    <SelectItem key={r.name} value={r.name}>
                                        {r.name}
                                    </SelectItem>
                                ))}
                            </SelectContent>
                        </Select>
                    </div>

                    <div className="w-px h-5 bg-border shrink-0" />

                    {/* top_k */}
                    <div className="flex items-center gap-2">
                        <Label className="text-sm text-muted-foreground font-mono whitespace-nowrap">top_k</Label>
                        <Input
                            type="number"
                            min={1}
                            max={15}
                            step={1}
                            value={topK}
                            onChange={(e) =>
                                setPrefs((p) => ({
                                    ...p,
                                    top_k: Math.min(15, Math.max(1, parseInt(e.target.value) || 1)),
                                }))
                            }
                            className="w-16 h-8 text-sm text-center"
                        />
                    </div>

                    {/* min_score */}
                    <div className="flex items-center gap-2">
                        <Switch
                            size="sm"
                            checked={useMinScore}
                            onCheckedChange={(checked) => setPrefs((p) => ({ ...p, use_min_score: checked }))}
                        />
                        <Label
                            className={`text-sm font-mono whitespace-nowrap ${
                                useMinScore ? 'text-muted-foreground' : 'text-muted-foreground/50'
                            }`}
                        >
                            min_score
                        </Label>
                        <Input
                            type="number"
                            min={0}
                            max={1}
                            step={0.01}
                            value={minScore}
                            disabled={!useMinScore}
                            onChange={(e) =>
                                setPrefs((p) => ({
                                    ...p,
                                    min_score: Math.min(1, Math.max(0, parseFloat(e.target.value) || 0)),
                                }))
                            }
                            className="w-16 h-8 text-sm text-center disabled:opacity-40"
                        />
                    </div>
                </div>
            </div>

            {/* Results */}
            <div className="flex-1 overflow-y-auto p-4 space-y-3">
                {error && (
                    <div className="rounded-md border border-destructive/50 bg-destructive/10 px-4 py-3 text-sm text-destructive">
                        {error}
                    </div>
                )}

                {loading && (
                    <div className="flex items-center justify-center py-16 text-muted-foreground text-sm">Поиск…</div>
                )}

                {result && !loading && (
                    <>
                        <div className="flex items-center justify-between text-xs text-muted-foreground px-0.5">
                            <span>
                                Найдено: <strong className="text-foreground">{result.meta.total}</strong>
                                {result.meta.search_all_limit != null && (
                                    <span className="ml-1 opacity-70">
                                        (лимит по всем репо: {result.meta.search_all_limit})
                                    </span>
                                )}
                            </span>
                            <span className="font-mono">
                                top_k={result.meta.top_k}
                                {result.meta.min_score != null && ` · min_score=${result.meta.min_score}`}
                            </span>
                        </div>

                        {result.chunks.length === 0 ? (
                            <div className="py-12 text-center text-muted-foreground text-sm">
                                Ничего не найдено. Попробуйте снизить min_score или изменить запрос.
                            </div>
                        ) : (
                            result.chunks.map((chunk) => <ChunkCard key={chunk.id} chunk={chunk} />)
                        )}
                    </>
                )}

                {!result && !loading && !error && (
                    <div className="py-16 text-center text-muted-foreground text-sm">
                        Введите запрос и нажмите «Искать»
                    </div>
                )}
            </div>
        </div>
    );
}
