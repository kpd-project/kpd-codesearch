import { StatsCard } from "./stats-card";
import { Database, HardDrive, Activity, Clock } from "lucide-react";

interface Repo {
  chunks: number;
}

interface StatsData {
  qdrant: { status: string; connected: boolean };
  repos: Repo[];
  uptime: string;
}

interface StatsGridProps {
  status: StatsData | null;
}

export function StatsGrid({ status }: StatsGridProps) {
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
      value: status?.repos.length ?? "—",
      isNumber: true,
    },
    {
      icon: Activity,
      label: "Всего векторов",
      value: status?.repos.reduce((sum, r) => sum + r.chunks, 0).toLocaleString() ?? "—",
      isNumber: true,
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
