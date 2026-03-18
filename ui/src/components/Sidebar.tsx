import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import { Plus, RotateCcw, Trash2, Loader2, CheckCircle2, Circle } from "lucide-react";
import { useRepos } from "@/hooks/useApi";
import { cn } from "@/lib/utils";

interface SidebarProps {
  className?: string;
}

export function Sidebar({ className }: SidebarProps) {
  const { repos, refetch } = useRepos();
  const [isAddOpen, setIsAddOpen] = useState(false);
  const [newRepoName, setNewRepoName] = useState("");
  const [newRepoPath, setNewRepoPath] = useState("");
  const [reindexing, setReindexing] = useState<string | null>(null);

  const handleAddRepo = async () => {
    if (!newRepoName || !newRepoPath) return;
    
    await fetch("/api/repos", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name: newRepoName, path: newRepoPath }),
    });
    
    setNewRepoName("");
    setNewRepoPath("");
    setIsAddOpen(false);
    refetch();
  };

  const handleRemoveRepo = async (name: string) => {
    if (!confirm(`Remove repository "${name}"?`)) return;
    
    await fetch(`/api/repos/${name}`, { method: "DELETE" });
    refetch();
  };

  const handleReindex = async (name: string) => {
    setReindexing(name);
    await fetch(`/api/repos/${name}/reindex`, { method: "POST" });
    // Will be updated via WebSocket
  };

  return (
    <div className={cn("w-64 bg-slate-900 border-r border-slate-800 flex flex-col", className)}>
      <div className="p-4 border-b border-slate-800">
        <h2 className="text-lg font-semibold text-slate-100">Repositories</h2>
      </div>
      
      <div className="flex-1 overflow-y-auto p-2">
        {repos.map((repo) => (
          <Card key={repo.name} className="mb-2 bg-slate-800 border-slate-700">
            <CardContent className="p-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  {repo.enabled ? (
                    <CheckCircle2 className="w-4 h-4 text-green-500" />
                  ) : (
                    <Circle className="w-4 h-4 text-slate-500" />
                  )}
                  <span className="text-sm text-slate-200 font-medium">{repo.name}</span>
                </div>
                <div className="flex items-center gap-1">
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => handleReindex(repo.name)}
                    disabled={reindexing === repo.name || repo.status === "indexing"}
                    title="Reindex"
                  >
                    {reindexing === repo.name || repo.status === "indexing" ? (
                      <Loader2 className="w-3 h-3 animate-spin" />
                    ) : (
                      <RotateCcw className="w-3 h-3" />
                    )}
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => handleRemoveRepo(repo.name)}
                    title="Remove"
                  >
                    <Trash2 className="w-3 h-3 text-red-400" />
                  </Button>
                </div>
              </div>
              <div className="mt-2 text-xs text-slate-400">
                {repo.chunks} chunks
                {repo.status === "indexing" && (
                  <span className="ml-2 text-yellow-400">Indexing...</span>
                )}
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      <div className="p-3 border-t border-slate-800">
        <Dialog open={isAddOpen} onOpenChange={setIsAddOpen}>
          <DialogTrigger>
            <Button variant="outline" className="w-full">
              <Plus className="w-4 h-4 mr-2" />
              Add Repository
            </Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Add Repository</DialogTitle>
            </DialogHeader>
            <div className="space-y-4 mt-4">
              <div>
                <Label htmlFor="repo-name">Name</Label>
                <Input
                  id="repo-name"
                  value={newRepoName}
                  onChange={(e) => setNewRepoName(e.target.value)}
                  placeholder="e.g., kpd-backend"
                />
              </div>
              <div>
                <Label htmlFor="repo-path">Path</Label>
                <Input
                  id="repo-path"
                  value={newRepoPath}
                  onChange={(e) => setNewRepoPath(e.target.value)}
                  placeholder="e.g., /path/to/repo"
                />
              </div>
              <Button onClick={handleAddRepo} className="w-full">Add</Button>
            </div>
          </DialogContent>
        </Dialog>
      </div>
    </div>
  );
}
