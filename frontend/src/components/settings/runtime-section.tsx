import { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Slider } from "@/components/ui/slider";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { Save, Sliders } from "lucide-react";

const MODELS = [
  { value: "google/gemini-2.0-flash-001", label: "Gemini 2.0 Flash" },
  { value: "google/gemini-2.5-flash-preview", label: "Gemini 2.5 Flash" },
  { value: "anthropic/claude-3-haiku", label: "Claude 3 Haiku" },
  { value: "openai/gpt-4o-mini", label: "GPT-4o Mini" },
];

interface RuntimeSettings {
  model: string;
  temperature: number;
  top_k: number;
  max_chunks: number;
  rag_mode: "simple" | "agent";
}

export function RuntimeSection() {
  const [settings, setSettings] = useState<RuntimeSettings>({
    model: MODELS[0].value,
    temperature: 0.1,
    top_k: 10,
    max_chunks: 10,
    rag_mode: "agent",
  });
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    fetch("/api/config")
      .then((res) => res.json())
      .then((data) => {
        if (data.settings) {
          const s = data.settings as Partial<RuntimeSettings>;
          setSettings((prev) => ({
            ...prev,
            ...s,
            rag_mode:
              s.rag_mode === "simple" || s.rag_mode === "agent"
                ? s.rag_mode
                : prev.rag_mode,
          }));
        }
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, []);

  const handleSave = async () => {
    setSaving(true);
    setSaved(false);
    try {
      await fetch("/api/config/runtime", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(settings),
      });
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    } finally {
      setSaving(false);
    }
  };

  if (loading) return <div>Загрузка...</div>;

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Sliders className="w-5 h-5" />
          Настройки выполнения
        </CardTitle>
        <p className="text-sm text-muted-foreground">
          Изменения применяются мгновенно без перезапуска
        </p>
      </CardHeader>
      <CardContent className="space-y-6">
        <div>
          <Label htmlFor="rag-mode">Режим RAG (runtime)</Label>
          <Select
            value={settings.rag_mode}
            onValueChange={(value) => {
              if (value === "simple" || value === "agent") {
                setSettings((s) => ({ ...s, rag_mode: value }));
              }
            }}
          >
            <SelectTrigger id="rag-mode" className="mt-1">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="simple">Простой (поиск + ответ)</SelectItem>
              <SelectItem value="agent">Агент (инструменты)</SelectItem>
            </SelectContent>
          </Select>
          <p className="text-xs text-muted-foreground mt-1">
            Меняется сразу для всего API после сохранения
          </p>
        </div>

        <div>
          <Label htmlFor="model">Модель LLM</Label>
          <Select
            value={settings.model}
            onValueChange={(value) => {
              if (value) {
                setSettings((s) => ({ ...s, model: value }));
              }
            }}
          >
            <SelectTrigger className="mt-1">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {MODELS.map((m) => (
                <SelectItem key={m.value} value={m.value}>
                  {m.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <div>
          <div className="flex justify-between">
            <Label>Температура</Label>
            <Badge variant="secondary">{settings.temperature.toFixed(2)}</Badge>
          </div>
          <Slider
            className="mt-3"
            min={0}
            max={2}
            step={0.05}
            value={[settings.temperature]}
            onValueChange={(value) => {
              const values = Array.isArray(value) ? value : [value];
              setSettings((s) => ({ ...s, temperature: values[0] || 0 }));
            }}
          />
          <p className="text-xs text-muted-foreground mt-1">
            Ниже — точнее, выше — креативнее
          </p>
        </div>

        <div>
          <div className="flex justify-between">
            <Label>Top-K (результаты поиска)</Label>
            <Badge variant="secondary">{settings.top_k}</Badge>
          </div>
          <Slider
            className="mt-3"
            min={1}
            max={15}
            value={[settings.top_k]}
            onValueChange={(value) => {
              const values = Array.isArray(value) ? value : [value];
              setSettings((s) => ({ ...s, top_k: values[0] || 1 }));
            }}
          />
        </div>

        <div>
          <Label htmlFor="max-chunks">Макс. чанков в контексте</Label>
          <Input
            id="max-chunks"
            type="number"
            min={1}
            max={20}
            className="mt-1"
            value={settings.max_chunks}
            onChange={(e) =>
              setSettings((s) => ({
                ...s,
                max_chunks: parseInt(e.target.value) || 1,
              }))
            }
          />
        </div>

        <div className="flex items-center gap-2">
          <Button onClick={handleSave} disabled={saving} className="w-full">
            <Save className="w-4 h-4 mr-2" />
            {saving
              ? "Сохранение…"
              : saved
              ? "Сохранено!"
              : "Сохранить настройки"}
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}