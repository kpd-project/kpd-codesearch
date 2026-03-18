import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";
import type { Repo } from "@/types/repo";

interface IndexingProgressProps {
  repos: Repo[];
  progress: Record<string, number>;
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
        {indexingRepos.map((repo) => (
          <div key={repo.name}>
            <div className="flex justify-between mb-1">
              <span className="text-sm text-muted-foreground">{repo.name}</span>
              <Badge variant="secondary">
                {progress[repo.name] !== undefined
                  ? `${progress[repo.name]}%`
                  : "—"}
              </Badge>
            </div>
            <Progress value={progress[repo.name] || 0} className="h-2" />
          </div>
        ))}
      </CardContent>
    </Card>
  );
}
