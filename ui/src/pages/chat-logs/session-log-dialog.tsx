import { useEffect, useState } from "react";
import { Copy, Download, Maximize2, Minimize2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  downloadSessionLogFile,
  getSessionLogRecord,
  type SessionLogRecord,
} from "@/lib/session-logs-idb";
import { cn } from "@/lib/utils";
import { formatPayloadAsJson, JsonHighlighter } from "./json-log-view";
import { SessionLogChatView } from "./session-log-chat-view";

const SESSION_LOG_DIALOG_UI_KEY = "kpd-codesearch-session-log-dialog-ui-v1";

function loadSessionLogDialogUi(): {
  expanded: boolean;
  viewTab: "chat" | "json";
} {
  if (typeof window === "undefined") {
    return { expanded: false, viewTab: "chat" };
  }
  try {
    const raw = localStorage.getItem(SESSION_LOG_DIALOG_UI_KEY);
    if (!raw) return { expanded: false, viewTab: "chat" };
    const parsed = JSON.parse(raw) as unknown;
    if (parsed == null || typeof parsed !== "object") {
      return { expanded: false, viewTab: "chat" };
    }
    const o = parsed as Record<string, unknown>;
    const expanded = o.expanded === true;
    const viewTab = o.viewTab === "json" ? "json" : "chat";
    return { expanded, viewTab };
  } catch {
    return { expanded: false, viewTab: "chat" };
  }
}

function saveSessionLogDialogUi(prefs: {
  expanded: boolean;
  viewTab: "chat" | "json";
}): void {
  try {
    localStorage.setItem(SESSION_LOG_DIALOG_UI_KEY, JSON.stringify(prefs));
  } catch {
    // квота / приватный режим
  }
}

function previewQuestion(payload: Record<string, unknown>): string {
  const q = payload.question;
  if (typeof q !== "string" || !q.trim()) return "—";
  const t = q.trim();
  return t.length > 100 ? `${t.slice(0, 100)}…` : t;
}

export interface SessionLogDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  /** id записи в IndexedDB */
  logId: string | null;
  /** Список уже отдал полную запись — без повторного чтения БД */
  initialRecord?: SessionLogRecord | null;
}

export function SessionLogDialog({
  open,
  onOpenChange,
  logId,
  initialRecord,
}: SessionLogDialogProps) {
  const [record, setRecord] = useState<SessionLogRecord | null>(null);
  const [loading, setLoading] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const [viewTab, setViewTab] = useState<"chat" | "json">("chat");
  const [expanded, setExpanded] = useState(false);

  useEffect(() => {
    if (!open || !logId) {
      setRecord(null);
      setLoading(false);
      setLoadError(null);
      setCopied(false);
      setViewTab("chat");
      return;
    }

    if (initialRecord != null && initialRecord.id === logId) {
      setRecord(initialRecord);
      setLoading(false);
      setLoadError(null);
      return;
    }

    let cancelled = false;
    setLoadError(null);
    setRecord(null);
    setLoading(true);
    void getSessionLogRecord(logId)
      .then((row) => {
        if (cancelled) return;
        setLoading(false);
        if (row) setRecord(row);
        else setLoadError("Запись не найдена в локальной базе.");
      })
      .catch((e) => {
        if (cancelled) return;
        console.error("getSessionLogRecord:", e);
        setLoading(false);
        setLoadError("Не удалось загрузить лог.");
      });

    return () => {
      cancelled = true;
    };
  }, [open, logId, initialRecord]);

  useEffect(() => {
    if (open && logId) setViewTab("chat");
  }, [open, logId]);

  useEffect(() => {
    if (!open) setExpanded(false);
  }, [open]);

  const selectedJson =
    record != null ? formatPayloadAsJson(record.payload) : "";

  const handleCopy = async () => {
    if (!selectedJson) return;
    try {
      await navigator.clipboard.writeText(selectedJson);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 2000);
    } catch (e) {
      console.error("clipboard:", e);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent
        showCloseButton
        className={cn(
          "flex w-[calc(100%-2rem)] flex-col gap-0 overflow-hidden p-0 sm:max-w-3xl md:max-w-4xl",
          expanded ? "h-[95vh] max-h-[95vh]" : "max-h-[min(85vh,720px)]"
        )}
      >
        <Button
          type="button"
          variant="ghost"
          size="icon-sm"
          className="absolute top-2 right-11 z-10"
          title={
            expanded ? "Свернуть окно" : "Развернуть на весь экран по высоте"
          }
          aria-label={expanded ? "Свернуть окно" : "Развернуть окно"}
          onClick={() => setExpanded((v) => !v)}
        >
          {expanded ? (
            <Minimize2 className="size-4" aria-hidden />
          ) : (
            <Maximize2 className="size-4" aria-hidden />
          )}
        </Button>
        <DialogHeader className="shrink-0 space-y-1 border-b border-border px-6 py-4">
          <DialogTitle className="text-left">Лог сессии</DialogTitle>
          <DialogDescription className="text-left line-clamp-2">
            {record != null
              ? previewQuestion(record.payload)
              : loadError ?? (loading ? "Загрузка…" : "…")}
          </DialogDescription>
          {record != null ? (
            <p className="text-xs text-muted-foreground pt-1">
              {new Date(record.createdAt).toLocaleString("ru-RU")} ·{" "}
              <code className="text-[0.7rem]">{record.id}</code>
            </p>
          ) : null}
        </DialogHeader>

        <div
          className={cn(
            "flex min-h-0 flex-1 flex-col px-6 py-4",
            expanded && "min-h-0 overflow-hidden"
          )}
        >
          {loadError ? (
            <p className="text-sm text-muted-foreground">{loadError}</p>
          ) : loading ? (
            <p className="text-sm text-muted-foreground">Загрузка…</p>
          ) : record != null ? (
            <Tabs
              value={viewTab}
              onValueChange={(v) => setViewTab(v as "chat" | "json")}
              className={cn(
                "flex min-h-0 flex-1 flex-col gap-3",
                expanded && "min-h-0 flex-1 overflow-hidden"
              )}
            >
              <TabsList className="h-9 w-full shrink-0 justify-start sm:w-auto">
                <TabsTrigger value="chat">Чат</TabsTrigger>
                <TabsTrigger value="json">JSON</TabsTrigger>
              </TabsList>
              <TabsContent
                value="chat"
                className="m-0 flex min-h-0 flex-1 flex-col overflow-hidden"
                keepMounted
              >
                <ScrollArea
                  className={cn(
                    "rounded-lg border border-border bg-muted/40",
                    expanded ? "min-h-0 flex-1 basis-0" : "h-[min(55vh,480px)]"
                  )}
                >
                  <div className="p-4">
                    <SessionLogChatView payload={record.payload} />
                  </div>
                </ScrollArea>
              </TabsContent>
              <TabsContent
                value="json"
                className="m-0 flex min-h-0 flex-1 flex-col overflow-hidden"
                keepMounted
              >
                <ScrollArea
                  className={cn(
                    "rounded-lg border border-border bg-muted/40",
                    expanded ? "min-h-0 flex-1 basis-0" : "h-[min(55vh,480px)]"
                  )}
                >
                  <div className="p-4">
                    <pre className="m-0 font-mono text-xs leading-relaxed whitespace-pre-wrap break-words">
                      <code className="text-foreground">
                        <JsonHighlighter text={selectedJson} />
                      </code>
                    </pre>
                  </div>
                </ScrollArea>
              </TabsContent>
            </Tabs>
          ) : null}
        </div>

        <div className="flex shrink-0 flex-wrap items-center justify-end gap-2 border-t border-border bg-muted/30 px-6 py-3">
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={() => void handleCopy()}
            disabled={!record || !selectedJson}
            title={copied ? "Скопировано" : "Копировать JSON в буфер"}
          >
            <Copy className="w-4 h-4 mr-1.5" aria-hidden />
            {copied ? "Скопировано" : "Копировать"}
          </Button>
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={() => record && void downloadSessionLogFile(record.id)}
            disabled={!record}
          >
            <Download className="w-4 h-4 mr-1.5" aria-hidden />
            Скачать JSON
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
