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
}

export function AddRepoDialog({
  open,
  onOpenChange,
  onAdd,
}: AddRepoDialogProps) {
  const [name, setName] = useState("");
  const [path, setPath] = useState("");

  const handleAdd = async () => {
    if (!name || !path) return;
    await onAdd(name, path);
    setName("");
    setPath("");
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
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Добавить репозиторий</DialogTitle>
        </DialogHeader>
        <div className="space-y-4 mt-4">
          <div>
            <Label htmlFor="repo-name">Название</Label>
            <Input
              id="repo-name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g., kpd-backend"
            />
          </div>
          <div>
            <Label htmlFor="repo-path">Путь</Label>
            <Input
              id="repo-path"
              value={path}
              onChange={(e) => setPath(e.target.value)}
              placeholder="e.g., d:/kpd-project/kpd-backend"
            />
          </div>
          <Button onClick={handleAdd} className="w-full">
            Добавить
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
