import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Info, Server, Database, GitBranch, Key } from "lucide-react";

interface SystemConfig {
  qdrant: { url: string; api_key_masked: string; has_api_key: boolean };
  embeddings: { model: string; dimension: number };
  repos: { base_path: string };
  llm: { base_url: string; api_key_masked: string; has_api_key: boolean };
}

export function SystemInfoSection() {
  const [config, setConfig] = useState<SystemConfig | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch("/api/config/system")
      .then((res) => res.json())
      .then((data) => {
        setConfig(data);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, []);

  if (loading) return <div>Загрузка...</div>;

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Server className="w-5 h-5" />
          Системные настройки
        </CardTitle>
        <p className="text-sm text-muted-foreground">
          Изменение требует редактирования .env и перезапуска приложения
        </p>
      </CardHeader>
      <CardContent className="space-y-6">
        <div className="space-y-2">
          <div className="flex items-center gap-2 font-medium">
            <Database className="w-4 h-4" />
            Qdrant
          </div>
          <InfoRow label="URL" value={config?.qdrant.url} />
          <InfoRow
            label="API Key"
            value={config?.qdrant.has_api_key ? "••••••••" : "не задан"}
          />
        </div>

        <div className="space-y-2">
          <div className="flex items-center gap-2 font-medium">
            <Key className="w-4 h-4" />
            Embeddings
          </div>
          <InfoRow label="Модель" value={config?.embeddings.model} />
          <InfoRow
            label="Размерность"
            value={config?.embeddings.dimension?.toString()}
          />
        </div>

        <div className="space-y-2">
          <div className="flex items-center gap-2 font-medium">
            <GitBranch className="w-4 h-4" />
            Репозитории
          </div>
          <InfoRow label="Базовый путь" value={config?.repos.base_path} />
        </div>

        <div className="space-y-2">
          <div className="flex items-center gap-2 font-medium">
            <Key className="w-4 h-4" />
            LLM (OpenAI-compatible)
          </div>
          <InfoRow label="Base URL" value={config?.llm.base_url} />
          <InfoRow
            label="API Key"
            value={config?.llm.has_api_key ? "••••••••" : "не задан"}
          />
        </div>

        <Alert>
          <Info className="size-4" aria-hidden />
          <AlertTitle>Системные настройки в .env</AlertTitle>
          <AlertDescription>
            Для изменения отредактируйте файл{" "}
            <code className="relative rounded bg-muted px-[0.3rem] py-[0.2rem] font-mono text-sm">
              .env
            </code>{" "}
            и перезапустите приложение
          </AlertDescription>
        </Alert>
      </CardContent>
    </Card>
  );
}

function InfoRow({ label, value }: { label: string; value?: string }) {
  return (
    <div className="flex gap-4 text-sm">
      <span className="text-muted-foreground w-32 shrink-0">{label}:</span>
      <span className="font-mono">{value || "—"}</span>
    </div>
  );
}