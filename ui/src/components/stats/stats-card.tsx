import type { LucideIcon } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";

interface StatsCardProps {
  icon: LucideIcon;
  label: string;
  value: string;
  connected?: boolean;
  isNumber?: boolean;
}

export function StatsCard({
  icon: Icon,
  label,
  value,
  connected,
  isNumber = false,
}: StatsCardProps) {
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between pb-2">
        <CardTitle className="text-sm font-medium text-muted-foreground">
          {label}
        </CardTitle>
        <Icon className="w-4 h-4 text-muted-foreground" />
      </CardHeader>
      <CardContent>
        <div className="flex items-center gap-2">
          {connected !== undefined && (
            <span
              className={cn(
                "w-3 h-3 rounded-full",
                connected
                  ? "bg-green-500"
                  : "bg-red-500"
              )}
            />
          )}
          <span
            className={cn(
              "font-semibold",
              isNumber ? "text-2xl font-bold" : "text-lg"
            )}
          >
            {value}
          </span>
        </div>
      </CardContent>
    </Card>
  );
}
