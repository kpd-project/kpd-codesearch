import { useCallback, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { Chat } from "@/components/chat";
import { Repositories } from "@/components/repositories";
import { useStatus } from "@/hooks/use-api";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";
import { Circle, Settings, HelpCircle } from "lucide-react";
import { ScrollArea } from "@/components/ui/scroll-area";
import { ThemeToggle } from "@/components/theme-toggle";
import { apiUrl } from "@/lib/api-url";
import { TestsLayout } from "@/pages/tests/tests-layout";

type RagQueryMode = "simple" | "agent";

function getActiveTab(pathname: string): string {
  if (pathname.startsWith("/chat")) return "chat";
  if (pathname.startsWith("/tests")) return "tests";
  return "repositories";
}

function AppShell() {
  const location = useLocation();
  const navigate = useNavigate();
  const activeTab = getActiveTab(location.pathname);
  const [ragSaving, setRagSaving] = useState(false);
  const { status, loading, refetch, wsConnected } = useStatus();

  const isConnected = wsConnected && status?.qdrant.connected;

  const ragMode: RagQueryMode =
    status?.settings?.rag_mode === "simple" ||
    status?.settings?.rag_mode === "agent"
      ? status.settings.rag_mode
      : "agent";

  const setRagMode = useCallback(
    async (m: RagQueryMode) => {
      if (m === ragMode) return;
      setRagSaving(true);
      try {
        const res = await fetch(apiUrl("/api/config/runtime"), {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ rag_mode: m }),
        });
        if (!res.ok) throw new Error("runtime");
        await refetch();
      } catch {
        /* ignore */
      } finally {
        setRagSaving(false);
      }
    },
    [ragMode, refetch]
  );

  const handleTabChange = useCallback(
    (value: string) => {
      if (value === "repositories") navigate("/");
      else if (value === "chat") navigate("/chat");
      else if (value === "tests") navigate("/tests/vector-search");
    },
    [navigate]
  );

  return (
    <Tabs value={activeTab} onValueChange={handleTabChange} className="h-screen flex flex-col bg-background text-foreground">
      {/* Header с навигацией */}
      <header className="h-14 border-b border-border flex items-center justify-between px-4 bg-background shrink-0">
        <div className="flex items-center gap-6">
          <div className="flex items-center gap-2 shrink-0">
            <span title={isConnected ? "Подключено" : "Отключено"}>
              <Circle
                className={`w-2 h-2 cursor-default ${
                  isConnected ? "fill-green-500 text-green-500" : "fill-red-500 text-red-500"
                }`}
              />
            </span>
            <h1 className="text-xl font-semibold text-primary" title="ASTRA-M">АСТРА-М</h1>
          </div>
          <TabsList className="h-8 bg-transparent p-0 gap-0 border-0">
            <TabsTrigger value="repositories" className="h-8 rounded-md px-3 py-0 text-sm data-[state=active]:bg-muted">
              Репозитории
            </TabsTrigger>
            <TabsTrigger value="chat" className="h-8 rounded-md px-3 py-0 text-sm data-[state=active]:bg-muted">
              Чат
            </TabsTrigger>
            <TabsTrigger value="tests" className="h-8 rounded-md px-3 py-0 text-sm data-[state=active]:bg-muted">
              Тесты
            </TabsTrigger>
          </TabsList>
        </div>
        <div className="flex items-center gap-2">
          <Link to="/settings">
            <Button variant="ghost" size="sm" title="Настройки">
              <Settings className="w-4 h-4" />
            </Button>
          </Link>
          <Button variant="ghost" size="sm" disabled title="Справка (скоро)">
            <HelpCircle className="w-4 h-4" />
          </Button>
          <ThemeToggle />
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1 overflow-hidden flex flex-col">
        <TabsContent value="repositories" className="flex-1 m-0 min-h-0" keepMounted>
          <ScrollArea className="h-full min-h-0">
            <Repositories status={status} loading={loading} refetch={refetch} />
          </ScrollArea>
        </TabsContent>

        <TabsContent value="chat" className="flex-1 m-0 min-h-0" keepMounted>
          <Chat
            className="h-full"
            ragMode={ragMode}
            onRagModeChange={setRagMode}
            ragModeDisabled={loading || ragSaving}
          />
        </TabsContent>

        <TabsContent value="tests" className="flex-1 m-0 min-h-0">
          <TestsLayout />
        </TabsContent>
      </main>

      {/* Footer */}
      <footer className="h-8 border-t border-border flex items-center justify-between px-4 text-xs text-muted-foreground bg-background shrink-0">
        <span className="flex items-center gap-2 min-w-0">
          <span className="shrink-0">Версия 2.0</span>
          <span className="text-border shrink-0" aria-hidden>
            ·
          </span>
          <Link
            to="/chat-logs"
            className="truncate hover:text-foreground underline-offset-2 hover:underline"
            title="Локальные логи сессий (IndexedDB)"
          >
            Логи чатов
          </Link>
        </span>
        <div className="flex items-center gap-3">
          <span className="flex items-center gap-1">
            <Circle className={`w-1.5 h-1.5 ${wsConnected ? "fill-green-500 text-green-500" : "fill-red-500 text-red-500"}`} />
            WS: {wsConnected ? "подключён" : "отключён"}
          </span>
          <span className="flex items-center gap-1">
            <Circle className={`w-1.5 h-1.5 ${status?.qdrant.connected ? "fill-green-500 text-green-500" : "fill-red-500 text-red-500"}`} />
            Qdrant: {status?.qdrant.status ?? "—"}
          </span>
        </div>
        <span className="shrink-0">Время работы: {status?.uptime ?? "—"}</span>
      </footer>
    </Tabs>
  );
}

export default function App() {
  return <AppShell />;
}
