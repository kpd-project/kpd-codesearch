import { useState } from "react";
import { useRepos } from "@/hooks/use-repos";
import type { RepoStatus } from "@/types/repo";
import { useRepoDescribe } from "@/hooks/use-repo-describe";
import { useSystemConfig } from "@/hooks/use-system-config";
import { StatsGrid } from "@/components/stats/stats-grid";
import {
  IndexingProgress,
  RepoCard,
  RepoCardModal,
  AddRepoDialog,
} from "@/components/repo";

interface RepositoriesProps {
  status: RepoStatus | null;
  loading: boolean;
  refetch: () => Promise<void>;
}

export function Repositories({ status, loading, refetch }: RepositoriesProps) {
  const { config } = useSystemConfig();
  const { addRepo, removeRepo, reindexRepo, toggleRepo, updateRepoCard } =
    useRepos(refetch);
  const { describing, describe } = useRepoDescribe(refetch);

  const basePath = config?.repos?.base_path || "";

  const [isAddOpen, setIsAddOpen] = useState(false);
  const [repoCardOpen, setRepoCardOpen] = useState(false);
  const [activeRepoName, setActiveRepoName] = useState<string | null>(null);

  const activeRepo = status?.repos.find((r) => r.name === activeRepoName) ?? null;

  const handleOpenRepoCard = (name: string) => {
    setActiveRepoName(name);
    setRepoCardOpen(true);
  };

  const handleOpenExistingFromAdd = (collectionName: string) => {
    setActiveRepoName(collectionName);
    setRepoCardOpen(true);
  };

  const handleReindex = async (name: string) => {
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
          onOpenExisting={handleOpenExistingFromAdd}
          basePath={basePath}
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
            onCreateIndex={handleReindex}
            onReindex={handleReindex}
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
        describing={describing}
        onRemove={removeRepo}
        onDescribe={describe}
        onSave={updateRepoCard}
      />
    </div>
  );
}
