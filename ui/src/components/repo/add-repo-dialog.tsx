import { useCallback, useEffect, useMemo, useState } from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { CircleHelp, Plus } from "lucide-react";
import type { RepoFolderCandidate } from "@/types/repo";
import { cn } from "@/lib/utils";

interface AddRepoDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onAdd: (name: string, path: string) => Promise<void>;
  onOpenExisting: (collectionName: string) => void;
  basePath?: string;
}

export function AddRepoDialog({
  open,
  onOpenChange,
  onAdd,
  onOpenExisting,
  basePath = "",
}: AddRepoDialogProps) {
  const [candidates, setCandidates] = useState<RepoFolderCandidate[]>([]);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [filter, setFilter] = useState("");
  const [selectedFolder, setSelectedFolder] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const loadCandidates = useCallback(async () => {
    setLoading(true);
    setLoadError(null);
    try {
      const res = await fetch("/api/repos/candidates");
      if (!res.ok) {
        const detail =
          (await res.json().catch(() => null))?.detail ??
          res.statusText;
        throw new Error(
          typeof detail === "string" ? detail : "Не удалось загрузить список папок"
        );
      }
      const data = await res.json();
      setCandidates(data.candidates ?? []);
    } catch (e) {
      setLoadError(e instanceof Error ? e.message : "Ошибка загрузки");
      setCandidates([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (open) {
      void loadCandidates();
      setFilter("");
      setSelectedFolder(null);
    }
  }, [open, loadCandidates]);

  const filtered = useMemo(() => {
    const q = filter.trim().toLowerCase();
    if (!q) return candidates;
    return candidates.filter((c) => c.folder.toLowerCase().includes(q));
  }, [candidates, filter]);

  const selected = useMemo(
    () => candidates.find((c) => c.folder === selectedFolder) ?? null,
    [candidates, selectedFolder]
  );

  const handleAdd = async () => {
    if (!selected || selected.already_added) return;
    setSubmitting(true);
    try {
      await onAdd(selected.folder, selected.relative_path);
      setSelectedFolder(null);
      onOpenChange(false);
    } finally {
      setSubmitting(false);
    }
  };

  const handleOpen = () => {
    if (!selected?.already_added || !selected.collection_name) return;
    onOpenExisting(selected.collection_name);
    onOpenChange(false);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogTrigger
        render={
          <Button variant="default" size="lg">
            <Plus className="w-4 h-4 mr-2" />
            Добавить репозиторий
          </Button>
        }
      />
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>Добавить репозиторий</DialogTitle>
        </DialogHeader>
        <div className="space-y-4 mt-2">
          <div className="space-y-1">
            <div className="flex items-center gap-1">
              <span className="text-muted-foreground text-sm">Базовый путь</span>
              <TooltipProvider>
                <Tooltip>
                  <TooltipTrigger aria-label="Справка о базовом пути">
                    <CircleHelp className="size-3.5" />
                  </TooltipTrigger>
                  <TooltipContent>
                    Список папок ниже — это подкаталоги этого каталога. Чтобы
                    изменить базовый путь, задайте переменную{" "}
                    <span className="font-mono">REPOS_BASE_PATH</span> в{" "}
                    <span className="font-mono">.env</span> и перезапустите
                    backend.
                  </TooltipContent>
                </Tooltip>
              </TooltipProvider>
            </div>
            <p className="text-foreground font-mono text-sm break-all">
              {basePath || "—"}
            </p>
          </div>

          {loadError && (
            <p className="text-destructive text-sm" role="alert">
              {loadError}
            </p>
          )}

          <div className="flex flex-col gap-2">
            <Label htmlFor="repo-folder-filter">Папка</Label>
            <Input
              id="repo-folder-filter"
              value={filter}
              onChange={(e) => setFilter(e.target.value)}
              placeholder="Поиск по имени…"
              disabled={loading || !!loadError}
            />
          </div>

          <ScrollArea className="h-[240px] rounded-lg border border-border">
            <div className="p-1">
              {loading && (
                <p className="text-muted-foreground text-sm p-3">Загрузка…</p>
              )}
              {!loading && !loadError && filtered.length === 0 && (
                <p className="text-muted-foreground text-sm p-3">
                  Нет подходящих папок
                </p>
              )}
              {!loading &&
                filtered.map((c) => {
                  const isSel = selectedFolder === c.folder;
                  return (
                    <button
                      key={c.folder}
                      type="button"
                      onClick={() => setSelectedFolder(c.folder)}
                      className={cn(
                        "flex w-full items-center justify-between gap-2 rounded-md px-3 py-2 text-left text-sm transition-colors",
                        isSel
                          ? "bg-accent text-accent-foreground"
                          : "hover:bg-muted/80"
                      )}
                    >
                      <span className="font-mono truncate">{c.folder}</span>
                      {c.already_added && (
                        <Badge
                          variant="outline"
                          className="shrink-0 border-amber-200/80 bg-amber-100 text-amber-950 dark:border-amber-800/80 dark:bg-amber-950/40 dark:text-amber-100"
                        >
                          Уже добавлено
                        </Badge>
                      )}
                    </button>
                  );
                })}
            </div>
          </ScrollArea>

          <div className="flex flex-col gap-2 sm:flex-row sm:justify-end">
            <Button
              type="button"
              variant="secondary"
              disabled={
                !selected?.already_added ||
                !selected.collection_name ||
                submitting
              }
              onClick={handleOpen}
              className="w-full sm:w-auto"
            >
              Открыть
            </Button>
            <Button
              type="button"
              disabled={
                !selected ||
                selected.already_added ||
                submitting ||
                loading
              }
              onClick={handleAdd}
              className="w-full sm:w-auto"
            >
              {submitting ? "Добавление…" : "Добавить"}
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
