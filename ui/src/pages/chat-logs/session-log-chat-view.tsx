import { Bot } from "lucide-react";
import { ChatMarkdownBody } from "@/lib/chat-markdown";
import { cn } from "@/lib/utils";

function formatTokenLine(n: number): string {
  return n > 0 ? n.toLocaleString("ru-RU") : "—";
}

function getString(obj: Record<string, unknown>, key: string): string | undefined {
  const v = obj[key];
  return typeof v === "string" ? v : undefined;
}

function getStringArray(obj: Record<string, unknown>, key: string): string[] {
  const v = obj[key];
  if (!Array.isArray(v)) return [];
  return v.filter((x): x is string => typeof x === "string");
}

function getUsage(obj: Record<string, unknown>): {
  pt: number;
  ct: number;
  tt: number;
} | null {
  const u = obj.usage;
  if (u == null || typeof u !== "object") return null;
  const o = u as Record<string, unknown>;
  const pt = Number(o.prompt_tokens ?? 0);
  const ct = Number(o.completion_tokens ?? 0);
  const tt = Number(o.total_tokens ?? pt + ct);
  if (!Number.isFinite(pt) || !Number.isFinite(ct) || !Number.isFinite(tt)) {
    return null;
  }
  return { pt, ct, tt };
}

interface ParsedToolCall {
  tool: string;
  argsStr: string;
  preview: string;
  resultLen?: number;
}

function parseToolCalls(obj: Record<string, unknown>): ParsedToolCall[] {
  const v = obj.tool_calls;
  if (!Array.isArray(v)) return [];
  const out: ParsedToolCall[] = [];
  for (const item of v) {
    if (item == null || typeof item !== "object") continue;
    const t = item as Record<string, unknown>;
    const tool = typeof t.tool === "string" ? t.tool : "";
    let argsStr = "";
    try {
      argsStr = JSON.stringify(t.args ?? {}, null, 2);
    } catch {
      argsStr = String(t.args);
    }
    const preview = typeof t.result_preview === "string" ? t.result_preview : "";
    const resultLen = typeof t.result_len === "number" ? t.result_len : undefined;
    out.push({
      tool: tool || "—",
      argsStr,
      preview,
      resultLen,
    });
  }
  return out;
}

function resolveAnswerText(payload: Record<string, unknown>): string {
  const ans = getString(payload, "answer");
  if (ans != null && ans.trim() !== "") return ans;
  const err = getString(payload, "error");
  if (err != null && err.trim() !== "") return err;
  return "—";
}

export interface SessionLogChatViewProps {
  payload: Record<string, unknown>;
  className?: string;
}

/** Просмотр сохранённого лога в виде переписки (как основной чат). */
export function SessionLogChatView({ payload, className }: SessionLogChatViewProps) {
  const question = getString(payload, "question")?.trim() ?? "";
  const steps = getStringArray(payload, "steps");
  const answerText = resolveAnswerText(payload);
  const usage = getUsage(payload);
  const durationRaw = payload.duration_s;
  const durationS =
    typeof durationRaw === "number" && Number.isFinite(durationRaw)
      ? durationRaw
      : undefined;
  const model = getString(payload, "model");
  const iterationsRaw = payload.iterations;
  const iterations =
    typeof iterationsRaw === "number" && Number.isFinite(iterationsRaw)
      ? iterationsRaw
      : undefined;
  const toolCalls = parseToolCalls(payload);
  const toolCallsCount =
    typeof payload.tool_calls_count === "number" &&
    Number.isFinite(payload.tool_calls_count)
      ? payload.tool_calls_count
      : toolCalls.length;

  return (
    <div className={cn("mx-auto w-full max-w-[120ch] space-y-4 py-1", className)}>
      <div className="flex justify-end">
        <div
          className={cn(
            "p-4 w-fit min-w-[min(100%,12rem)] max-w-full",
            "rounded-tl-2xl rounded-tr-2xl rounded-bl-2xl rounded-br-none",
            "bg-linear-to-br from-blue-500/40 from-0% via-blue-500/18 via-45% to-secondary text-secondary-foreground",
            "dark:from-blue-400/35 dark:via-blue-500/15 dark:to-secondary"
          )}
        >
          <div className="text-xs mb-1 font-semibold opacity-70">Вы</div>
          <div className="text-sm whitespace-pre-wrap break-words">
            {question || "—"}
          </div>
        </div>
      </div>

      <div className="flex justify-start">
        <div
          className={cn(
            "p-4 w-fit min-w-[min(100%,12rem)] max-w-full",
            "rounded-tl-2xl rounded-tr-2xl rounded-br-2xl rounded-bl-none bg-muted text-foreground"
          )}
        >
          <div className="text-xs mb-1 font-semibold flex items-center gap-1.5 text-muted-foreground">
            <Bot className="h-4 w-4 shrink-0" strokeWidth={2} aria-hidden />
            <span>Ассистент</span>
          </div>

          {steps.length > 0 ? (
            <div className="text-xs text-muted-foreground mb-2 space-y-1 border-b border-border/60 pb-2">
              {steps.map((line, i) => (
                <p key={i} className="leading-snug">
                  {line}
                </p>
              ))}
            </div>
          ) : null}

          <ChatMarkdownBody content={answerText} variant="assistant" />

          {(usage != null || durationS != null || toolCallsCount > 0 || model != null || iterations != null) && (
            <div className="text-xs text-muted-foreground mt-2 pt-2 border-t border-border/60 space-y-1.5">
              {usage != null ? (
                <p>
                  <span className="text-foreground/80">Токены:</span> всего{" "}
                  {formatTokenLine(usage.tt)} · на вход:{" "}
                  {formatTokenLine(usage.pt)} · на выход:{" "}
                  {formatTokenLine(usage.ct)}
                </p>
              ) : null}
              {durationS != null ? (
                <p>
                  <span className="text-foreground/80">Время ответа:</span>{" "}
                  {durationS.toFixed(1)} с
                </p>
              ) : null}
              <p>
                <span className="text-foreground/80">Вызовы инструментов:</span>{" "}
                {toolCallsCount}
              </p>
              {model != null ? (
                <p>
                  <span className="text-foreground/80">Модель:</span> {model}
                </p>
              ) : null}
              {iterations != null ? (
                <p>
                  <span className="text-foreground/80">Итерации:</span> {iterations}
                </p>
              ) : null}
            </div>
          )}

          {toolCalls.length > 0 ? (
            <div className="mt-3 pt-3 border-t border-border/60 space-y-3">
              <p className="text-xs font-semibold text-foreground/90">Инструменты</p>
              {toolCalls.map((tc, idx) => (
                <div key={idx} className="space-y-1.5">
                  <p className="text-xs font-medium text-foreground">{tc.tool}</p>
                  <pre className="m-0 max-h-40 overflow-auto rounded-md border border-border bg-background/80 p-2 font-mono text-[0.7rem] leading-relaxed text-foreground">
                    {tc.argsStr}
                  </pre>
                  {tc.preview !== "" ? (
                    <pre className="m-0 max-h-48 overflow-auto rounded-md border border-border bg-background/80 p-2 font-mono text-[0.7rem] leading-relaxed whitespace-pre-wrap break-words text-foreground">
                      {tc.preview}
                      {tc.resultLen != null ? (
                        <span className="block mt-1 text-muted-foreground">
                          (result_len: {tc.resultLen})
                        </span>
                      ) : null}
                    </pre>
                  ) : null}
                </div>
              ))}
            </div>
          ) : null}
        </div>
      </div>
    </div>
  );
}
