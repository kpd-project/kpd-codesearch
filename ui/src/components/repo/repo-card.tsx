import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Switch } from "@/components/ui/switch";
import { Button } from "@/components/ui/button";
import { Play } from "lucide-react";
import type { Repo } from "@/types/repo";

interface RepoCardProps {
  repo: Repo;
  onClick: (name: string) => void;
  onToggle: (name: string, enabled: boolean) => void;
  onCreateIndex?: (name: string) => void;
}

export function RepoCard({
  repo,
  onClick,
  onToggle,
  onCreateIndex,
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

  return (
    <Card
      onClick={() => onClick(repo.name)}
      className="cursor-pointer hover:bg-muted/50 transition-colors"
      role="button"
      tabIndex={0}
      onKeyDown={handleKeyDown}
    >
      <CardContent className="px-4 py-1">
        <div className="flex items-start justify-between gap-4">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-1">
              <span className="font-semibold uppercase text-lg text-foreground">
                {repo.name}
              </span>
              {repo.status === "indexing" && (
                <Badge variant="secondary" className="text-yellow-500">
                  Индексация…
                </Badge>
              )}
              {repo.status === "error" && (
                <Badge variant="destructive">Ошибка</Badge>
              )}
            </div>

            <div className="text-xs text-muted-foreground mb-2">
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
              <p className="text-sm text-muted-foreground leading-relaxed">
                {repo.description}
              </p>
            ) : (
              <p className="text-sm text-muted-foreground/50 italic">
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
