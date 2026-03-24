import { StatsCard } from "./stats-card";
import { Database, HardDrive, Activity, Clock } from "lucide-react";

interface Repo {
  chunks: number;
  enabled: boolean;
}

interface StatsData {
  qdrant: { status: string; connected: boolean };
  repos: Repo[];
  uptime: string;
}

interface StatsGridProps {
  status: StatsData | null;
}

function getVectorsParts(
  status: StatsData | null
): { primary: string; secondary: string } | null {
  if (!status?.repos) return null;
  const total = status.repos.reduce((sum, r) => sum + r.chunks, 0);
  const active = status.repos
    .filter((r) => r.enabled)
    .reduce((sum, r) => sum + r.chunks, 0);
  return {
    primary: active.toLocaleString(),
    secondary: total.toLocaleString(),
  };
}

function getReposParts(
  status: StatsData | null
): { primary: string; secondary: string } | null {
  if (!status?.repos) return null;
  const enabled = status.repos.filter((r) => r.enabled).length;
  return {
    primary: String(enabled),
    secondary: String(status.repos.length),
  };
}

export function StatsGrid({ status }: StatsGridProps) {
  const vectorsParts = getVectorsParts(status);
  const reposParts = getReposParts(status);

  const stats = [
    {
      icon: Database,
      label: "Статус Qdrant",
      value: status?.qdrant.status ?? "—",
      connected: status?.qdrant.connected,
    },
    {
      icon: HardDrive,
      label: "Репозитории",
      value: reposParts ? reposParts.primary : "—",
      valueSecondary: reposParts?.secondary,
      isNumber: true,
    },
    {
      icon: Activity,
      label: "Всего векторов",
      value: vectorsParts ? vectorsParts.primary : "—",
      valueSecondary: vectorsParts?.secondary,
      isNumber: true,
      hint:
        "Слева — по включённым репозиториям (участвуют в поиске). Справа — сумма по всем коллекциям в Qdrant.",
    },
    {
      icon: Clock,
      label: "Время работы",
      value: status?.uptime ?? "—",
    },
  ];

  return (
    <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
      {stats.map((stat) => (
        <StatsCard key={stat.label} {...stat} />
      ))}
    </div>
  );
}
