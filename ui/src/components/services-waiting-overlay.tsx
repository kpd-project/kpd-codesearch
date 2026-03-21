import { Circle } from "lucide-react";
import { useStatus } from "@/hooks/use-api";

/** Текст вместо прочерка, если статус Qdrant ещё не пришёл или пришёл как пустой/тире. */
function qdrantStatusForOverlay(raw: string | undefined): string {
  const s = raw?.trim() ?? "";
  if (s === "" || s === "—" || s === "-") return "неизвестно";
  return s;
}

/** Рендерит оверлей, пока WS и Qdrant не готовы (глобальный гейт у корня приложения). */
export function ServicesWaitingGate() {
  const { status, wsConnected } = useStatus();
  const servicesReady = Boolean(wsConnected && status?.qdrant.connected);
  return (
    <ServicesWaitingOverlay
      open={!servicesReady}
      wsConnected={wsConnected}
      qdrantConnected={Boolean(status?.qdrant.connected)}
      qdrantStatusLabel={qdrantStatusForOverlay(status?.qdrant.status)}
    />
  );
}

/** Блокирующий оверлей: пока WS или Qdrant недоступны — весь UI под ним. */
export function ServicesWaitingOverlay({
  open,
  wsConnected,
  qdrantConnected,
  qdrantStatusLabel,
}: {
  open: boolean;
  wsConnected: boolean;
  qdrantConnected: boolean;
  /** Текст статуса Qdrant из API или запасной вариант. */
  qdrantStatusLabel: string;
}) {
  if (!open) return null;

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="services-wait-title"
      className="fixed inset-0 z-100 flex items-center justify-center bg-background/85 p-4 supports-backdrop-filter:backdrop-blur-sm"
    >
      <div className="w-full max-w-sm rounded-xl border border-border bg-card p-6 text-sm shadow-lg ring-1 ring-foreground/10">
        <h2 id="services-wait-title" className="text-base font-medium text-foreground">
          Ожидание сервисов
        </h2>
        <ul className="mt-4 flex flex-col gap-3">
          <li className="flex items-center gap-2">
            <Circle
              className={`h-2 w-2 shrink-0 ${
                wsConnected ? "fill-primary text-primary" : "fill-destructive text-destructive"
              }`}
              aria-hidden
            />
            <span className="text-foreground">
              <span className="font-medium">WS</span>
              <span className="text-muted-foreground"> — </span>
              {wsConnected ? "подключён" : "отключён"}
            </span>
          </li>
          <li className="flex items-center gap-2">
            <Circle
              className={`h-2 w-2 shrink-0 ${
                qdrantConnected ? "fill-primary text-primary" : "fill-destructive text-destructive"
              }`}
              aria-hidden
            />
            <span className="text-foreground">
              <span className="font-medium">Qdrant</span>
              <span className="text-muted-foreground"> — </span>
              {qdrantStatusLabel}
            </span>
          </li>
        </ul>
      </div>
    </div>
  );
}
