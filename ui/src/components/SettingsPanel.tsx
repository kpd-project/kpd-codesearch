import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Slider } from "@/components/ui/slider";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { SettingsIcon, Save } from "lucide-react";

const MODELS = [
  { value: "google/gemini-2.0-flash-001", label: "Gemini 2.0 Flash" },
  { value: "google/gemini-2.5-flash-preview", label: "Gemini 2.5 Flash" },
  { value: "anthropic/claude-3-haiku", label: "Claude 3 Haiku" },
  { value: "openai/gpt-4o-mini", label: "GPT-4o Mini" },
];

interface Settings {
  model: string;
  temperature: number;
  top_k: number;
  max_chunks: number;
}

interface SettingsPanelProps {
  className?: string;
}

export function SettingsPanel({ className }: SettingsPanelProps) {
  const [settings, setSettings] = useState<Settings>({
    model: MODELS[0].value,
    temperature: 0.1,
    top_k: 10,
    max_chunks: 10,
  });
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    fetch("/api/config")
      .then((res) => res.json())
      .then((data) => {
        if (data.settings) {
          setSettings(data.settings);
        }
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, []);

  const handleSave = async () => {
    setSaving(true);
    try {
      await fetch("/api/config/runtime", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(settings),
      });
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return <div className="p-4">Loading...</div>;
  }

  return (
    <div className={className}>
      <Card className="bg-slate-800 border-slate-700">
        <CardHeader>
          <CardTitle className="text-slate-100 flex items-center gap-2">
            <SettingsIcon className="w-5 h-5" />
            Runtime Settings
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Model */}
          <div>
            <Label htmlFor="model">LLM Model</Label>
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

          {/* Temperature */}
          <div>
            <div className="flex justify-between">
              <Label>Temperature</Label>
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
            <p className="text-xs text-slate-500 mt-1">
              Lower = more focused, Higher = more creative
            </p>
          </div>

          {/* Top-K */}
          <div>
            <div className="flex justify-between">
              <Label>Top-K (search results)</Label>
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

          {/* Max Chunks */}
          <div>
            <Label htmlFor="max-chunks">Max Chunks for Context</Label>
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

          <Button onClick={handleSave} disabled={saving} className="w-full">
            <Save className="w-4 h-4 mr-2" />
            {saving ? "Saving..." : "Save Settings"}
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
