import { useStatus } from "@/hooks/useApi";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";
import { Database, HardDrive, Clock, Activity, Circle } from "lucide-react";

export function Dashboard() {
  const { status, loading } = useStatus();

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <p className="text-slate-500">Loading...</p>
      </div>
    );
  }

  const totalRepos = status?.repos.length || 0;
  const totalChunks = status?.repos.reduce((sum, r) => sum + r.chunks, 0) || 0;
  const indexingRepos = status?.repos.filter((r) => r.status === "indexing") || [];

  return (
    <div className="p-6 space-y-6">
      <h2 className="text-2xl font-semibold text-slate-100">Dashboard</h2>

      {/* Status Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card className="bg-slate-800 border-slate-700">
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-slate-400">
              Qdrant Status
            </CardTitle>
            <Database className="w-4 h-4 text-slate-400" />
          </CardHeader>
          <CardContent>
            <div className="flex items-center gap-2">
              <Circle
                className={`w-3 h-3 ${
                  status?.qdrant.connected ? "fill-green-500 text-green-500" : "fill-red-500 text-red-500"
                }`}
              />
              <span className="text-lg font-semibold text-slate-100">
                {status?.qdrant.status || "unknown"}
              </span>
            </div>
          </CardContent>
        </Card>

        <Card className="bg-slate-800 border-slate-700">
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-slate-400">
              Repositories
            </CardTitle>
            <HardDrive className="w-4 h-4 text-slate-400" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-slate-100">{totalRepos}</div>
          </CardContent>
        </Card>

        <Card className="bg-slate-800 border-slate-700">
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-slate-400">
              Total Chunks
            </CardTitle>
            <Activity className="w-4 h-4 text-slate-400" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-slate-100">
              {totalChunks.toLocaleString()}
            </div>
          </CardContent>
        </Card>

        <Card className="bg-slate-800 border-slate-700">
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-slate-400">
              Uptime
            </CardTitle>
            <Clock className="w-4 h-4 text-slate-400" />
          </CardHeader>
          <CardContent>
            <div className="text-lg font-semibold text-slate-100">
              {status?.uptime || "N/A"}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Indexing Progress */}
      {indexingRepos.length > 0 && (
        <Card className="bg-slate-800 border-slate-700">
          <CardHeader>
            <CardTitle className="text-slate-100">Indexing Progress</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {indexingRepos.map((repo) => (
              <div key={repo.name}>
                <div className="flex justify-between mb-1">
                  <span className="text-sm text-slate-300">{repo.name}</span>
                  <Badge variant="secondary">
                    {status?.indexing_progress?.[repo.name] || 0}%
                  </Badge>
                </div>
                <Progress
                  value={status?.indexing_progress?.[repo.name] || 0}
                  className="h-2"
                />
              </div>
            ))}
          </CardContent>
        </Card>
      )}

      {/* Repositories Table */}
      <Card className="bg-slate-800 border-slate-700">
        <CardHeader>
          <CardTitle className="text-slate-100">Repositories</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            {status?.repos.map((repo) => (
              <div
                key={repo.name}
                className="flex items-center justify-between p-3 rounded-lg bg-slate-700/50"
              >
                <div>
                  <div className="font-medium text-slate-200">{repo.name}</div>
                  <div className="text-xs text-slate-500">{repo.path}</div>
                </div>
                <div className="text-right">
                  <div className="text-sm text-slate-300">
                    {repo.chunks.toLocaleString()} chunks
                  </div>
                  {repo.last_indexed && (
                    <div className="text-xs text-slate-500">
                      Last indexed: {new Date(repo.last_indexed).toLocaleString()}
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
