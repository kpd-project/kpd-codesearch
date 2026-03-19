import { useCallback } from "react";

interface RepoCardUpdatePayload {
  display_name: string | null;
  relative_path: string | null;
  short_description: string;
  description: string;
}

export function useRepos(refetch: () => Promise<void>) {
  const addRepo = useCallback(
    async (name: string, path: string) => {
      await fetch("/api/repos", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name, path }),
      });
      await refetch();
    },
    [refetch]
  );

  const removeRepo = useCallback(
    async (name: string): Promise<boolean> => {
      if (!confirm(`Удалить репозиторий «${name}»?`)) return false;
      await fetch(`/api/repos/${name}`, { method: "DELETE" });
      await refetch();
      return true;
    },
    [refetch]
  );

  const reindexRepo = useCallback(async (name: string) => {
    await fetch(`/api/repos/${name}/reindex`, { method: "POST" });
  }, []);

  const toggleRepo = useCallback(
    async (name: string, enabled: boolean) => {
      await fetch(`/api/repos/${name}/enabled`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ enabled }),
      });
      await refetch();
    },
    [refetch]
  );

  const updateRepoCard = useCallback(
    async (name: string, payload: RepoCardUpdatePayload) => {
      await fetch(`/api/repos/${name}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      await refetch();
    },
    [refetch]
  );

  return { addRepo, removeRepo, reindexRepo, toggleRepo, updateRepoCard };
}
