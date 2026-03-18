import { useState } from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogFooter,
  DialogClose,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Loader2, RotateCcw, Trash2, Sparkles } from "lucide-react";
import type { Repo } from "@/types/repo";

interface RepoCardModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  repo: Repo | null;
  reindexing: string | null;
  describing: string | null;
  onReindex: (name: string) => void;
  onRemove: (name: string) => Promise<boolean>;
  onDescribe: (name: string) => void;
}

export function RepoCardModal({
  open,
  onOpenChange,
  repo,
  reindexing,
  describing,
  onReindex,
  onRemove,
  onDescribe,
}: RepoCardModalProps) {
  const [isRemoving, setIsRemoving] = useState(false);

  const handleClose = (newOpen: boolean) => {
    onOpenChange(newOpen);
    if (!newOpen) {
      setIsRemoving(false);
    }
  };

  const handleRemove = async () => {
    if (!repo) return;
    setIsRemoving(true);
    const removed = await onRemove(repo.name);
    if (removed) {
      handleClose(false);
    } else {
      setIsRemoving(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent
        showCloseButton={false}
        className="max-w-2xl w-[calc(100%-2rem)] max-h-[85vh] overflow-y-auto"
      >
        <DialogHeader>
          <DialogTitle>Карточка репозитория</DialogTitle>
        </DialogHeader>

        {!repo ? (
          <div className="text-sm text-muted-foreground">Репозиторий не найден.</div>
        ) : (
          <div className="space-y-5">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              <div>
                <Label htmlFor="repo-name-readonly">Название</Label>
                <Input
                  id="repo-name-readonly"
                  readOnly
                  value={repo.name}
                  className="mt-1"
                />
              </div>
              <div>
                <Label htmlFor="repo-chunks-readonly">Количество векторов</Label>
                <Input
                  id="repo-chunks-readonly"
                  readOnly
                  value={repo.chunks.toLocaleString()}
                  className="mt-1"
                />
              </div>
              <div className="md:col-span-2">
                <Label htmlFor="repo-last-indexed-readonly">Последняя индексация</Label>
                <Input
                  id="repo-last-indexed-readonly"
                  readOnly
                  value={
                    repo.last_indexed
                      ? new Date(repo.last_indexed).toLocaleString("ru")
                      : repo.chunks > 0
                        ? "Неизвестно"
                        : "Никогда"
                  }
                  className="mt-1"
                />
              </div>
            </div>

            <div className="space-y-2">
              <div className="flex items-center justify-between gap-3">
                <Label>Описание</Label>
                {!repo.description && (
                  <Button
                    variant="secondary"
                    size="sm"
                    onClick={() => onDescribe(repo.name)}
                    disabled={describing === repo.name}
                    title="Сгенерировать описание"
                  >
                    {describing === repo.name ? (
                      <Loader2 className="w-4 h-4 animate-spin mr-2" />
                    ) : (
                      <Sparkles className="w-4 h-4 text-primary mr-2" />
                    )}
                    Сгенерировать
                  </Button>
                )}
              </div>

              {repo.description ? (
                <Textarea readOnly value={repo.description} />
              ) : (
                <div className="rounded-lg border border-dashed border-border px-3 py-2 text-sm text-muted-foreground/80">
                  Описание отсутствует.
                </div>
              )}
            </div>

            <div className="space-y-2">
              <Label>Метаданные (JSON)</Label>
              <pre className="text-xs whitespace-pre-wrap wrap-break-word rounded-lg bg-muted/40 border border-border/60 p-3 max-h-[30vh] overflow-auto">
                {JSON.stringify(repo, null, 2)}
              </pre>
            </div>

            <div className="flex flex-wrap items-center gap-2 pt-2">
              <Button
                variant="secondary"
                size="sm"
                onClick={() => onReindex(repo.name)}
                disabled={reindexing === repo.name || repo.status === "indexing"}
                title="Переиндексировать"
              >
                {reindexing === repo.name || repo.status === "indexing" ? (
                  <Loader2 className="w-4 h-4 animate-spin mr-2" />
                ) : (
                  <RotateCcw className="w-4 h-4 mr-2" />
                )}
                Переиндексировать
              </Button>

              <Button
                variant="destructive"
                size="sm"
                onClick={handleRemove}
                disabled={reindexing === repo.name || isRemoving}
                title="Удалить"
              >
                <Trash2 className="w-4 h-4 mr-2" />
                Удалить
              </Button>
            </div>
          </div>
        )}

        <DialogFooter>
          <DialogClose render={<Button variant="outline">Закрыть</Button>} />
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
