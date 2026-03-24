import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";
import type { Repo, IndexingProgressEntry } from "@/types/repo";

interface IndexingProgressProps {
  repos: Repo[];
  progress: Record<string, IndexingProgressEntry>;
}

function barPercent(p: IndexingProgressEntry | undefined): number {
  if (!p?.total) return 0;
  return Math.min(100, Math.round((p.current / p.total) * 100));
}

export function IndexingProgress({ repos, progress }: IndexingProgressProps) {
  const indexingRepos = repos.filter((r) => r.status === "indexing");

  if (indexingRepos.length === 0) return null;

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-foreground">Прогресс индексации</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {indexingRepos.map((repo) => {
          const p = progress[repo.name];
          const pct = barPercent(p);
          return (
            <div key={repo.name}>
              <div className="flex justify-between gap-2 mb-1">
                <span className="text-sm text-muted-foreground truncate">
                  {repo.name}
                </span>
                <Badge variant="secondary" className="shrink-0">
                  {!p
                    ? "Запуск…"
                    : p.total > 0
                      ? `${p.current}/${p.total} файлов · ${pct}%`
                      : "—"}
                </Badge>
              </div>
              {p?.path ? (
                <p
                  className="text-xs text-muted-foreground truncate mb-1"
                  title={p.path}
                >
                  {p.path}
                </p>
              ) : null}
              <Progress value={pct} className="h-2" />
            </div>
          );
        })}
      </CardContent>
    </Card>
  );
}
