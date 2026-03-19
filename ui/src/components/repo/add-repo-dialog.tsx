import { useState } from "react";
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
import { Plus } from "lucide-react";

interface AddRepoDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onAdd: (name: string, path: string) => Promise<void>;
  basePath?: string;
}

export function AddRepoDialog({
  open,
  onOpenChange,
  onAdd,
  basePath = "",
}: AddRepoDialogProps) {
  const [name, setName] = useState("");
  const [path, setPath] = useState("");

  const handleAdd = async () => {
    console.log("handleAdd called", { name, path });
    if (!name || !path) {
      console.log("Empty fields, returning");
      return;
    }
    console.log("Calling onAdd");
    try {
      await onAdd(name, path);
      console.log("onAdd completed");
    } finally {
      setName("");
      setPath("");
      onOpenChange(false);
    }
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
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Добавить репозиторий</DialogTitle>
        </DialogHeader>
        <div className="space-y-4 mt-4">
          <div>
            <Label htmlFor="repo-name">Название</Label>
            <input
              id="repo-name"
              value={name}
              onChange={(e) => {
                console.log("name changed:", e.target.value);
                setName(e.target.value);
              }}
              placeholder="e.g., kpd-backend"
              className="flex h-8 w-full min-w-0 rounded-lg border border-input bg-transparent px-3 py-1 text-base"
            />
          </div>
          <div>
            <Label htmlFor="repo-path">Путь</Label>
            <div className="flex items-center gap-2">
              {basePath && (
                <span className="text-muted-foreground text-sm shrink-0">
                  {basePath}/
                </span>
              )}
              <Input
                id="repo-path"
                value={path}
                onChange={(e) => setPath(e.target.value)}
                placeholder="kpd-backend"
              />
            </div>
          </div>
          <Button onClick={handleAdd} className="w-full">
            Добавить
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
