import { CircleHelp, type LucideIcon } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";

interface StatsCardProps {
  icon: LucideIcon;
  label: string;
  value: string;
  /** Второе число (всего) — второстепенным стилем после «/». */
  valueSecondary?: string;
  connected?: boolean;
  isNumber?: boolean;
  /** Подсказка у заголовка (иконка «?»). */
  hint?: string;
}

export function StatsCard({
  icon: Icon,
  label,
  value,
  valueSecondary,
  connected,
  isNumber = false,
  hint,
}: StatsCardProps) {
  const valueClass = cn(
    "font-semibold tabular-nums",
    isNumber ? "text-2xl font-bold" : "text-lg"
  );

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between pb-2">
        <CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-1 min-w-0">
          <span className="truncate">{label}</span>
          {hint ? (
            <span
              className="inline-flex shrink-0"
              title={hint}
              aria-label={hint}
            >
              <CircleHelp className="w-3.5 h-3.5 text-muted-foreground cursor-help" />
            </span>
          ) : null}
        </CardTitle>
        <Icon className="w-4 h-4 text-muted-foreground shrink-0" />
      </CardHeader>
      <CardContent>
        <div className="flex items-center gap-2">
          {connected !== undefined && (
            <span
              className={cn(
                "w-3 h-3 rounded-full",
                connected ? "bg-green-500" : "bg-red-500"
              )}
            />
          )}
          {valueSecondary !== undefined ? (
            <span className="inline-flex items-baseline flex-wrap gap-x-1">
              <span className={valueClass}>{value}</span>
              <span className={cn(valueClass, "text-muted-foreground")}>
                / {valueSecondary}
              </span>
            </span>
          ) : (
            <span className={valueClass}>{value}</span>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
