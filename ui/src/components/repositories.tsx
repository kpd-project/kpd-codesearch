import { useState } from "react";
import { useStatus } from "@/hooks/use-api";
import { useRepos } from "@/hooks/use-repos";
import { useRepoDescribe } from "@/hooks/use-repo-describe";
import { StatsGrid } from "@/components/stats/stats-grid";
import {
  IndexingProgress,
  RepoCard,
  RepoCardModal,
  AddRepoDialog,
} from "@/components/repo";

export function Repositories() {
  const { status, loading, refetch } = useStatus();
  const { addRepo, removeRepo, reindexRepo, toggleRepo } = useRepos(refetch);
  const { describing, describe } = useRepoDescribe(refetch);

  const [isAddOpen, setIsAddOpen] = useState(false);
  const [reindexing, setReindexing] = useState<string | null>(null);
  const [repoCardOpen, setRepoCardOpen] = useState(false);
  const [activeRepoName, setActiveRepoName] = useState<string | null>(null);

  const activeRepo = status?.repos.find((r) => r.name === activeRepoName) ?? null;

  const handleOpenRepoCard = (name: string) => {
    setActiveRepoName(name);
    setRepoCardOpen(true);
  };

  const handleReindex = async (name: string) => {
    setReindexing(name);
    await reindexRepo(name);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <p className="text-muted-foreground">Загрузка…</p>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-semibold text-foreground">Репозитории</h2>
        <AddRepoDialog
          open={isAddOpen}
          onOpenChange={setIsAddOpen}
          onAdd={addRepo}
        />
      </div>

      <StatsGrid status={status} />

      <IndexingProgress
        repos={status?.repos || []}
        progress={status?.indexing_progress || {}}
      />

      <div className="space-y-3">
        {status?.repos.map((repo) => (
          <RepoCard
            key={repo.name}
            repo={repo}
            onClick={handleOpenRepoCard}
            onToggle={toggleRepo}
          />
        ))}
      </div>

      <RepoCardModal
        open={repoCardOpen}
        onOpenChange={(open) => {
          setRepoCardOpen(open);
          if (!open) setActiveRepoName(null);
        }}
        repo={activeRepo}
        reindexing={reindexing}
        describing={describing}
        onReindex={handleReindex}
        onRemove={removeRepo}
        onDescribe={describe}
      />
    </div>
  );
}
