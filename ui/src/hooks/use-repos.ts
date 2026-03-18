import { useCallback } from "react";

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

  return { addRepo, removeRepo, reindexRepo, toggleRepo };
}
