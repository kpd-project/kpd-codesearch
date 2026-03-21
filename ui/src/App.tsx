import { useState } from "react";
import { Link } from "react-router-dom";
import { Chat } from "@/components/chat";
import { Repositories } from "@/components/repositories";
import { useStatus } from "@/hooks/use-api";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";
import { Circle, Settings, HelpCircle } from "lucide-react";
import { ScrollArea } from "@/components/ui/scroll-area";
import { ThemeToggle } from "@/components/theme-toggle";

export default function App() {
  const [activeTab, setActiveTab] = useState("chat");
  const { status, loading, refetch, wsConnected } = useStatus();

  const isConnected = wsConnected && status?.qdrant.connected;

  return (
    <Tabs value={activeTab} onValueChange={setActiveTab} className="h-screen flex flex-col bg-background text-foreground">
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
          <TabsList className="h-9 bg-transparent p-0 gap-0 border-0">
            <TabsTrigger value="chat" className="rounded-md px-3 py-1.5 data-[state=active]:bg-muted">Чат</TabsTrigger>
            <TabsTrigger value="repositories" className="rounded-md px-3 py-1.5 data-[state=active]:bg-muted">Репозитории</TabsTrigger>
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
        <TabsContent value="chat" className="flex-1 m-0 min-h-0" keepMounted>
          <Chat className="h-full" />
        </TabsContent>

        <TabsContent value="repositories" className="flex-1 m-0 min-h-0" keepMounted>
          <ScrollArea className="h-full min-h-0">
            <Repositories status={status} loading={loading} refetch={refetch} />
          </ScrollArea>
        </TabsContent>
      </main>

      {/* Footer */}
      <footer className="h-8 border-t border-border flex items-center justify-between px-4 text-xs text-muted-foreground bg-background shrink-0">
        <span>Версия 2.0</span>
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
