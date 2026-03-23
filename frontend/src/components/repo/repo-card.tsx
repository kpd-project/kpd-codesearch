import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { Switch } from "@/components/ui/switch";
import { Button } from "@/components/ui/button";
import { Play, RefreshCw } from "lucide-react";
import type { Repo } from "@/types/repo";

interface RepoCardProps {
  repo: Repo;
  onClick: (name: string) => void;
  onToggle: (name: string, enabled: boolean) => void;
  onCreateIndex?: (name: string) => void;
  onReindex?: (name: string) => void;
}

export function RepoCard({
  repo,
  onClick,
  onToggle,
  onCreateIndex,
  onReindex,
}: RepoCardProps) {
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      onClick(repo.name);
    }
  };

  const neverIndexed = repo.chunks === 0 && !repo.last_indexed;
  const switchTitle = neverIndexed
    ? "Репозиторий недоступен до первой индексации"
    : repo.enabled
    ? "Отключить репозиторий"
    : "Включить репозиторий";

  const title = repo.display_name?.trim() ? repo.display_name.trim() : null;
  const inactive = !repo.enabled;
  const titleClass = cn(
    "uppercase text-lg font-semibold",
    inactive ? "text-muted-foreground" : "text-foreground"
  );

  return (
    <Card
      onClick={() => onClick(repo.name)}
      className={cn(
        "cursor-pointer transition-colors",
        inactive
          ? "bg-muted/40 hover:bg-muted/55 ring-foreground/5"
          : "hover:bg-muted/50"
      )}
      role="button"
      tabIndex={0}
      onKeyDown={handleKeyDown}
    >
      <CardContent className="px-4 py-1">
        <div className="flex items-start justify-between gap-4">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-1">
              {title ? (
                <span className={titleClass}>{title}</span>
              ) : (
                <span
                  className={cn(
                    "min-w-0 truncate font-mono text-lg font-semibold",
                    inactive ? "text-muted-foreground" : "text-foreground"
                  )}
                  title={repo.name}
                >
                  {repo.name}
                </span>
              )}
              {repo.status === "indexing" && (
                <Badge
                  variant="secondary"
                  className={cn(
                    inactive
                      ? "border-border bg-muted/50 text-muted-foreground"
                      : "text-yellow-500"
                  )}
                >
                  Индексация…
                </Badge>
              )}
              {repo.status === "error" && (
                <Badge
                  variant="destructive"
                  className={cn(inactive && "opacity-70")}
                >
                  Ошибка
                </Badge>
              )}
            </div>

            <div
              className={cn(
                "text-xs mb-2",
                inactive ? "text-muted-foreground/70" : "text-muted-foreground"
              )}
            >
              <span>{repo.chunks.toLocaleString()} векторов</span>
              <span className="mx-1">·</span>
              <span>
                {repo.last_indexed
                  ? `Последняя индексация: ${new Date(
                      repo.last_indexed
                    ).toLocaleString("ru")}`
                  : repo.chunks > 0
                  ? "Последняя индексация: Неизвестно"
                  : "Последняя индексация: Никогда не индексировался"}
              </span>
            </div>

            {repo.description ? (
              <p
                className={cn(
                  "text-sm leading-relaxed",
                  inactive ? "text-muted-foreground/80" : "text-muted-foreground"
                )}
              >
                {repo.description}
              </p>
            ) : (
              <p
                className={cn(
                  "text-sm italic",
                  inactive ? "text-muted-foreground/40" : "text-muted-foreground/50"
                )}
              >
                Нет описания
              </p>
            )}
          </div>

          <div
            className="flex flex-row items-center gap-2 shrink-0 mr-1"
            onClick={(e) => e.stopPropagation()}
            role="presentation"
          >
            {neverIndexed && onCreateIndex && (
              <Button
                variant="secondary"
                size="sm"
                onClick={() => onCreateIndex(repo.name)}
                disabled={repo.status === "indexing"}
                title="Создать индекс"
              >
                <Play className="w-4 h-4 mr-2" />
                Создать индекс
              </Button>
            )}
            {!neverIndexed && onReindex && (
              <Button
                variant="secondary"
                size="sm"
                onClick={() => onReindex(repo.name)}
                disabled={repo.status === "indexing"}
                title="Переиндексировать"
              >
                <RefreshCw className="w-4 h-4 mr-2" />
                Переиндексировать
              </Button>
            )}
            <Switch
              checked={repo.enabled}
              disabled={neverIndexed}
              onCheckedChange={(v) => onToggle(repo.name, v)}
              title={switchTitle}
            />
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
