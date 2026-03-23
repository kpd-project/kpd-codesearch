import { useState, useCallback } from "react";

export function useRepoDescribe(refetch: () => Promise<void>) {
  const [describing, setDescribing] = useState<string | null>(null);

  const describe = useCallback(
    async (name: string) => {
      setDescribing(name);
      try {
        await fetch(`/api/repos/${name}/describe`, { method: "POST" });
        await refetch();
      } finally {
        setDescribing(null);
      }
    },
    [refetch]
  );

  return { describing, describe };
}
