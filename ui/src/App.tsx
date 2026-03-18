import { useState } from "react";
import { Sidebar } from "@/components/Sidebar";
import { Chat } from "@/components/Chat";
import { Dashboard } from "@/components/Dashboard";
import { SettingsPanel } from "@/components/SettingsPanel";
import { useWebSocket, useStatus } from "@/hooks/useApi";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";
import { Circle, Settings, HelpCircle } from "lucide-react";

export default function App() {
  const [activeTab, setActiveTab] = useState("chat");
  const { connected } = useWebSocket();
  const { status } = useStatus();

  return (
    <div className="h-screen flex flex-col bg-slate-950 text-slate-100">
      {/* Header */}
      <header className="h-14 border-b border-slate-800 flex items-center justify-between px-4 bg-slate-900">
        <div className="flex items-center gap-3">
          <h1 className="text-xl font-semibold text-blue-400">KPD CodeSearch</h1>
          <div className="flex items-center gap-1 text-xs">
            <Circle
              className={`w-2 h-2 ${
                connected && status?.qdrant.connected
                  ? "fill-green-500 text-green-500"
                  : "fill-red-500 text-red-500"
              }`}
            />
            <span className="text-slate-400">
              {connected && status?.qdrant.connected ? "Connected" : "Disconnected"}
            </span>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="ghost" size="sm">
            <Settings className="w-4 h-4" />
          </Button>
          <Button variant="ghost" size="sm">
            <HelpCircle className="w-4 h-4" />
          </Button>
        </div>
      </header>

      {/* Main Content */}
      <div className="flex-1 flex overflow-hidden">
        <Sidebar />

        <main className="flex-1 overflow-hidden">
          <Tabs value={activeTab} onValueChange={setActiveTab} className="h-full flex flex-col">
            <TabsList className="mx-4 mt-4 bg-slate-800 border-slate-700">
              <TabsTrigger value="chat">Chat</TabsTrigger>
              <TabsTrigger value="dashboard">Dashboard</TabsTrigger>
              <TabsTrigger value="settings">Settings</TabsTrigger>
            </TabsList>

            <TabsContent value="chat" className="flex-1 m-0">
              <Chat className="h-full" />
            </TabsContent>

            <TabsContent value="dashboard" className="flex-1 m-0 overflow-auto">
              <Dashboard />
            </TabsContent>

            <TabsContent value="settings" className="flex-1 m-0 p-4 overflow-auto">
              <div className="max-w-md">
                <SettingsPanel />
              </div>
            </TabsContent>
          </Tabs>
        </main>
      </div>

      {/* Footer */}
      <footer className="h-8 border-t border-slate-800 flex items-center justify-between px-4 text-xs text-slate-500 bg-slate-900">
        <span>Version 2.0</span>
        <span>Qdrant: {status?.qdrant.status || "unknown"}</span>
        <span>Uptime: {status?.uptime || "N/A"}</span>
      </footer>
    </div>
  );
}
