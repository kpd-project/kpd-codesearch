import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ArrowLeft, Download, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  listAllSessionLogs,
  downloadSessionLogFile,
  type SessionLogRecord,
} from "@/lib/session-logs-idb";
import { cn } from "@/lib/utils";
import { SessionLogDialog } from "./session-log-dialog";

function previewQuestion(payload: Record<string, unknown>): string {
  const q = payload.question;
  if (typeof q !== "string" || !q.trim()) return "—";
  const t = q.trim();
  return t.length > 100 ? `${t.slice(0, 100)}…` : t;
}

function formatDuration(payload: Record<string, unknown>): string {
  const d = payload.duration_s;
  if (typeof d === "number" && Number.isFinite(d)) return `${d.toFixed(1)} с`;
  return "—";
}

export default function ChatLogsPage() {
  const [rows, setRows] = useState<SessionLogRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState<SessionLogRecord | null>(null);

  const load = () => {
    setLoading(true);
    void listAllSessionLogs()
      .then(setRows)
      .catch((e) => console.error("list session logs:", e))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    load();
  }, []);

  return (
    <div className="h-screen flex flex-col bg-background text-foreground">
      <header className="h-14 border-b border-border flex items-center justify-between px-4 shrink-0">
        <div className="flex items-center gap-4 min-w-0">
          <Link to="/">
            <Button variant="ghost" size="sm">
              <ArrowLeft className="w-4 h-4 mr-2" />
              Назад
            </Button>
          </Link>
          <h1 className="text-xl font-semibold truncate">Логи чатов</h1>
        </div>
        <Button
          type="button"
          variant="ghost"
          size="sm"
          title="Обновить список"
          onClick={load}
          disabled={loading}
        >
          <RefreshCw
            className={cn("w-4 h-4", loading && "animate-spin")}
            aria-hidden
          />
        </Button>
      </header>

      <ScrollArea className="flex-1 min-h-0">
        <div className="max-w-4xl mx-auto p-6">
          <p className="text-sm text-muted-foreground mb-4">
            Записи из локальной базы (IndexedDB) на этом устройстве. В меню не
            выводятся — открывайте по ссылке внизу главного экрана или по адресу{" "}
            <code className="text-xs bg-muted px-1 py-0.5 rounded">/chat-logs</code>
            .
          </p>

          {loading && rows.length === 0 ? (
            <p className="text-muted-foreground text-sm">Загрузка…</p>
          ) : rows.length === 0 ? (
            <p className="text-muted-foreground text-sm">
              Пока нет сохранённых логов. Они появляются после ответов ассистента
              в чате.
            </p>
          ) : (
            <ul className="space-y-2 border border-border rounded-lg divide-y divide-border">
              {rows.map((row) => (
                <li
                  key={row.id}
                  role="button"
                  tabIndex={0}
                  className="p-3 flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between sm:gap-4 cursor-pointer outline-none hover:bg-muted/50 focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background"
                  onClick={() => setSelected(row)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" || e.key === " ") {
                      e.preventDefault();
                      setSelected(row);
                    }
                  }}
                >
                  <div className="min-w-0 flex-1 space-y-1">
                    <p className="text-sm font-medium text-foreground line-clamp-2">
                      {previewQuestion(row.payload)}
                    </p>
                    <p className="text-xs text-muted-foreground">
                      {new Date(row.createdAt).toLocaleString("ru-RU")} ·{" "}
                      {formatDuration(row.payload)} · id:{" "}
                      <code className="text-[0.7rem]">{row.id.slice(0, 8)}…</code>
                    </p>
                  </div>
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    className="shrink-0 self-start sm:self-center"
                    onClick={(e) => {
                      e.stopPropagation();
                      void downloadSessionLogFile(row.id);
                    }}
                  >
                    <Download className="w-4 h-4 mr-1.5" aria-hidden />
                    Скачать JSON
                  </Button>
                </li>
              ))}
            </ul>
          )}
        </div>
      </ScrollArea>

      <SessionLogDialog
        open={selected != null}
        onOpenChange={(open) => {
          if (!open) setSelected(null);
        }}
        logId={selected?.id ?? null}
        initialRecord={selected}
      />
    </div>
  );
}
