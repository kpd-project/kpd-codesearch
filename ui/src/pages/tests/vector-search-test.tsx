import { useState } from "react";
import { useStatus } from "@/hooks/use-api";
import { apiUrl } from "@/lib/api-url";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { Switch } from "@/components/ui/switch";
import { Search, ChevronDown, ChevronUp } from "lucide-react";

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

function ChunkCard({ chunk }: { chunk: ChunkResult }) {
  const [expanded, setExpanded] = useState(false);

  const scoreColor =
    chunk.score >= 0.75
      ? "bg-green-500/15 text-green-700 dark:text-green-400"
      : chunk.score >= 0.5
      ? "bg-yellow-500/15 text-yellow-700 dark:text-yellow-400"
      : "bg-red-500/15 text-red-600 dark:text-red-400";

  return (
    <div className="border border-border rounded-lg bg-card text-card-foreground">
      {/* Header */}
      <div
        className="flex items-start gap-3 px-4 py-3 cursor-pointer select-none"
        onClick={() => setExpanded((v) => !v)}
      >
        <span className={`mt-0.5 shrink-0 text-xs font-mono font-semibold px-1.5 py-0.5 rounded ${scoreColor}`}>
          {chunk.score.toFixed(3)}
        </span>
        <div className="flex-1 min-w-0">
          <div className="flex flex-wrap items-center gap-1.5 mb-0.5">
            <span className="text-sm font-medium truncate">{chunk.path}</span>
            {chunk.name && (
              <Badge variant="outline" className="text-xs font-mono shrink-0">
                {chunk.name}
              </Badge>
            )}
          </div>
          <div className="flex flex-wrap gap-1.5 text-xs text-muted-foreground">
            <span>{chunk.repo}</span>
            {chunk.language && <span>· {chunk.language}</span>}
            {chunk.type && <span>· {chunk.type}</span>}
            <span className="ml-auto font-mono opacity-60">{chunk.id.slice(0, 8)}…</span>
          </div>
        </div>
        <span className="shrink-0 text-muted-foreground">
          {expanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
        </span>
      </div>

      {/* Content */}
      {expanded && (
        <div className="border-t border-border px-4 py-3">
          <pre className="text-xs font-mono whitespace-pre-wrap wrap-break-word leading-relaxed text-foreground/90 max-h-96 overflow-y-auto">
            {chunk.content}
          </pre>
        </div>
      )}
    </div>
  );
}

export function VectorSearchTest() {
  const { status } = useStatus();
  const repos = status?.repos ?? [];

  const [query, setQuery] = useState("");
  const [repo, setRepo] = useState<string>("__all__");
  const [topK, setTopK] = useState(5);
  const [minScore, setMinScore] = useState(0.5);
  const [useMinScore, setUseMinScore] = useState(true);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<SearchResponse | null>(null);

  const handleSearch = async () => {
    if (!query.trim()) return;
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const res = await fetch(apiUrl("/api/tests/vector-search"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          query: query.trim(),
          repo: repo === "__all__" ? null : repo,
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
      setError(e instanceof Error ? e.message : "Неизвестная ошибка");
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) handleSearch();
  };

  return (
    <div className="h-full flex flex-col">
      {/* Search Form */}
      <div className="shrink-0 border-b border-border bg-background p-4 space-y-4">
        <div className="flex gap-2">
          <Input
            placeholder="Поисковый запрос…"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={handleKeyDown}
            className="flex-1 font-mono text-sm"
          />
          <Button onClick={handleSearch} disabled={loading || !query.trim()}>
            <Search className="w-4 h-4 mr-1.5" />
            Искать
          </Button>
        </div>

        <div className="flex flex-wrap items-center gap-4">
          {/* Repo selector */}
          <div className="flex items-center gap-2">
            <Label className="text-sm text-muted-foreground whitespace-nowrap">Репозиторий</Label>
            <Select value={repo} onValueChange={setRepo}>
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
              onChange={(e) => setTopK(Math.min(15, Math.max(1, parseInt(e.target.value) || 1)))}
              className="w-16 h-8 text-sm text-center"
            />
          </div>

          {/* min_score */}
          <div className="flex items-center gap-2">
            <Switch
              size="sm"
              checked={useMinScore}
              onCheckedChange={setUseMinScore}
            />
            <Label className={`text-sm font-mono whitespace-nowrap ${useMinScore ? "text-muted-foreground" : "text-muted-foreground/50"}`}>
              min_score
            </Label>
            <Input
              type="number"
              min={0}
              max={1}
              step={0.01}
              value={minScore}
              disabled={!useMinScore}
              onChange={(e) => setMinScore(Math.min(1, Math.max(0, parseFloat(e.target.value) || 0)))}
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
          <div className="flex items-center justify-center py-16 text-muted-foreground text-sm">
            Поиск…
          </div>
        )}

        {result && !loading && (
          <>
            <div className="flex items-center justify-between text-xs text-muted-foreground px-0.5">
              <span>
                Найдено: <strong className="text-foreground">{result.meta.total}</strong>
                {result.meta.search_all_limit != null && (
                  <span className="ml-1 opacity-70">(лимит по всем репо: {result.meta.search_all_limit})</span>
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
              result.chunks.map((chunk) => (
                <ChunkCard key={chunk.id} chunk={chunk} />
              ))
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
