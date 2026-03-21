import { useState, useRef, useEffect } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type { Components } from "react-markdown";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Send, Trash2, Loader2, Bot } from "lucide-react";
import { cn } from "@/lib/utils";
import { putSessionLog } from "@/lib/session-logs-idb";
import { SessionLogDialog } from "@/pages/chat-logs/session-log-dialog";

/** Статистика ответа (из SSE meta), подвал под текстом */
interface AnswerFooterMeta {
  duration_s: number;
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
  tool_calls_count: number;
  /** Ключ записи в IndexedDB (полный JSON лога) */
  log_id: string;
}

interface Message {
  role: "user" | "assistant";
  content: string;
  /** Ход агента (как в Telegram) до появления текста ответа */
  status?: string;
  answerFooter?: AnswerFooterMeta;
}

/** Один локальный чат; версия ключа — при смене формата данных. */
const CHAT_STORAGE_KEY = "kpd-codesearch-chat-messages-v5";

function isAnswerFooterMeta(v: unknown): v is AnswerFooterMeta {
  if (v == null || typeof v !== "object") return false;
  const o = v as Record<string, unknown>;
  return (
    typeof o.duration_s === "number" &&
    typeof o.prompt_tokens === "number" &&
    typeof o.completion_tokens === "number" &&
    typeof o.total_tokens === "number" &&
    typeof o.tool_calls_count === "number" &&
    typeof o.log_id === "string"
  );
}

function formatTokenLine(n: number): string {
  return n > 0 ? n.toLocaleString("ru-RU") : "—";
}

function loadMessagesFromStorage(): Message[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = localStorage.getItem(CHAT_STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw) as unknown;
    if (!Array.isArray(parsed)) return [];
    return parsed
      .map((item) => {
        if (item == null || typeof item !== "object") return null;
        const m = item as Message;
        if (
          m.role === "assistant" &&
          m.answerFooter != null &&
          !isAnswerFooterMeta(m.answerFooter)
        ) {
          return { ...m, answerFooter: undefined };
        }
        return m;
      })
      .filter(
        (m): m is Message =>
          m != null &&
          typeof m === "object" &&
          (m.role === "user" || m.role === "assistant") &&
          typeof m.content === "string" &&
          (m.status === undefined || typeof m.status === "string") &&
          (m.answerFooter === undefined || isAnswerFooterMeta(m.answerFooter))
      );
  } catch {
    return [];
  }
}

function saveMessagesToStorage(messages: Message[]) {
  try {
    localStorage.setItem(CHAT_STORAGE_KEY, JSON.stringify(messages));
  } catch {
    // квота / приватный режим
  }
}

const markdownComponents: Components = {
  a: ({ className, href, children, ...props }) => (
    <a
      href={href}
      className={cn("underline underline-offset-2", className)}
      target="_blank"
      rel="noopener noreferrer"
      {...props}
    >
      {children}
    </a>
  ),
};

interface ChatProps {
  className?: string;
}

export function Chat({ className }: ChatProps) {
  const [messages, setMessages] = useState<Message[]>(loadMessagesFromStorage);
  const [input, setInput] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);
  const [sessionLogModalId, setSessionLogModalId] = useState<string | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const lastAutoScrollAtRef = useRef<number>(0);

  useEffect(() => {
    saveMessagesToStorage(messages);
  }, [messages]);

  useEffect(() => {
    const now = Date.now();

    // Во время стриминга `messages` меняются на каждом чанкe ответа.
    // Если прокручивать "smooth" на каждое обновление, скролл начинает дергаться.
    if (isStreaming && now - lastAutoScrollAtRef.current < 200) return;
    lastAutoScrollAtRef.current = now;

    scrollRef.current?.scrollIntoView({
      block: "end",
      behavior: isStreaming ? "auto" : "smooth",
    });
  }, [messages, isStreaming]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isStreaming) return;

    const userMessage = input.trim();
    setInput("");
    setMessages((prev) => [...prev, { role: "user", content: userMessage }]);
    setIsStreaming(true);

    try {
      const response = await fetch("/api/query", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: userMessage }),
      });

      if (!response.ok) throw new Error("Query failed");

      const reader = response.body?.getReader();
      if (!reader) throw new Error("No response body");

      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: "",
          status: "🤔 Думаю...",
          answerFooter: undefined,
        },
      ]);

      const appendToAssistant = (delta: string) => {
        setMessages((prev) => {
          const last = prev[prev.length - 1];
          if (last?.role === "assistant") {
            const nextContent = last.content + delta;
            return [
              ...prev.slice(0, -1),
              {
                ...last,
                content: nextContent,
                status: last.content === "" ? undefined : last.status,
              },
            ];
          }
          return prev;
        });
      };

      const setAssistantStatus = (text: string) => {
        setMessages((prev) => {
          const last = prev[prev.length - 1];
          if (last?.role === "assistant") {
            return [
              ...prev.slice(0, -1),
              { ...last, status: text },
            ];
          }
          return prev;
        });
      };

      const consumeSsePayload = (payload: string) => {
        if (payload === "[DONE]") return;
        try {
          const parsed = JSON.parse(payload) as {
            type?: string;
            text?: string;
            content?: string;
            error?: string;
            duration_s?: number;
            usage?: Record<string, unknown>;
            tool_calls_count?: number;
            session_log?: Record<string, unknown>;
          };
          if (parsed.error) {
            appendToAssistant(`\n\nОшибка: ${parsed.error}`);
            return;
          }
          if (parsed.type === "meta" && typeof parsed.duration_s === "number") {
            const duration_s = parsed.duration_s;
            void (async () => {
              const u = parsed.usage || {};
              const pt = Number(u.prompt_tokens ?? 0);
              const ct = Number(u.completion_tokens ?? 0);
              const tt = Number(u.total_tokens ?? pt + ct);
              let logId = "";
              if (parsed.session_log && typeof parsed.session_log === "object") {
                const id = crypto.randomUUID();
                try {
                  await putSessionLog(id, {
                    ...parsed.session_log,
                    client_log_id: id,
                  });
                  logId = id;
                } catch (e) {
                  console.error("session log IDB:", e);
                }
              }
              const footer: AnswerFooterMeta = {
                duration_s,
                prompt_tokens: pt,
                completion_tokens: ct,
                total_tokens: tt,
                tool_calls_count: Number(parsed.tool_calls_count ?? 0),
                log_id: logId,
              };
              setMessages((prev) => {
                const last = prev[prev.length - 1];
                if (last?.role === "assistant") {
                  return [
                    ...prev.slice(0, -1),
                    {
                      ...last,
                      status: undefined,
                      answerFooter: footer,
                    },
                  ];
                }
                return prev;
              });
            })();
            return;
          }
          if (parsed.type === "status" && parsed.text != null) {
            setAssistantStatus(parsed.text);
            return;
          }
          if (parsed.content != null && parsed.content !== "") {
            appendToAssistant(parsed.content);
          }
        } catch {
          appendToAssistant(payload);
        }
      };

      let sseBuffer = "";
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        sseBuffer += new TextDecoder().decode(value, { stream: true });
        const lines = sseBuffer.split("\n");
        sseBuffer = lines.pop() ?? "";

        for (const line of lines) {
          if (!line.startsWith("data: ")) continue;
          consumeSsePayload(line.slice(6));
        }
      }
      if (sseBuffer.startsWith("data: ")) {
        consumeSsePayload(sseBuffer.slice(6));
      }
    } catch (error) {
      console.error("Query error:", error);
      setMessages((prev) => {
        const last = prev[prev.length - 1];
        if (last?.role === "assistant") {
          return [
            ...prev.slice(0, -1),
            {
              ...last,
              content: last.content
                ? `${last.content}\n\nОшибка: не удалось получить ответ`
                : "Ошибка: не удалось получить ответ",
              status: undefined,
              answerFooter: undefined,
            },
          ];
        }
        return [
          ...prev,
          {
            role: "assistant",
            content: "Ошибка: не удалось получить ответ",
            answerFooter: undefined,
          },
        ];
      });
    } finally {
      setIsStreaming(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  const clearChat = () => setMessages([]);

  return (
    <div className={cn("flex flex-col h-full", className)}>
      <ScrollArea className="flex-1 min-h-0">
        <div className="mx-auto w-full max-w-[120ch] px-4 py-4 space-y-4">
          {messages.length === 0 && (
            <div className="text-center text-muted-foreground mt-20">
              <p>Спросите что угодно о вашем коде!</p>
              <p className="text-sm mt-2">
                Например: «Как работает аутентификация?»
              </p>
            </div>
          )}

          {messages.map((msg, i) => (
            <div
              key={i}
              className={cn(
                "flex",
                msg.role === "user" ? "justify-end" : "justify-start"
              )}
            >
              <div
                className={cn(
                  "p-4 w-fit min-w-[min(100%,12rem)] max-w-full",
                  msg.role === "user"
                    ? "rounded-tl-2xl rounded-tr-2xl rounded-bl-2xl rounded-br-none bg-linear-to-br from-blue-500/40 from-0% via-blue-500/18 via-45% to-secondary text-secondary-foreground dark:from-blue-400/35 dark:via-blue-500/15 dark:to-secondary"
                    : "rounded-tl-2xl rounded-tr-2xl rounded-br-2xl rounded-bl-none bg-muted text-foreground"
                )}
              >
                <div
                  className={cn(
                    "text-xs mb-1 font-semibold",
                    msg.role === "user"
                      ? "opacity-70"
                      : "flex items-center gap-1.5 text-muted-foreground"
                  )}
                >
                  {msg.role === "user" ? (
                    "Вы"
                  ) : (
                    <>
                      <Bot
                        className="h-4 w-4 shrink-0"
                        strokeWidth={2}
                        aria-hidden
                      />
                      <span>Ассистент</span>
                    </>
                  )}
                </div>
                {msg.role === "assistant" && msg.status && (
                  <div className="text-xs text-muted-foreground mb-2 flex items-start gap-2 border-b border-border/60 pb-2">
                    <Loader2 className="h-3.5 w-3.5 shrink-0 mt-0.5 animate-spin" />
                    <span className="leading-snug flex-1 min-w-0">{msg.status}</span>
                  </div>
                )}
                <div
                  className={cn(
                    "prose prose-lg prose-neutral max-w-none break-words [&_pre]:max-w-full [&_pre]:overflow-x-auto",
                    "[&_ul]:list-disc [&_ul]:pl-6 [&_ol]:list-decimal [&_ol]:pl-6 [&_strong]:font-semibold [&_code]:rounded-md [&_code]:bg-muted/80 [&_code]:px-1.5 [&_code]:py-0.5 [&_code]:text-[0.9em]",
                    msg.role === "user"
                      ? "text-secondary-foreground dark:prose-invert"
                      : "text-foreground dark:prose-invert"
                  )}
                >
                  <ReactMarkdown
                    remarkPlugins={[remarkGfm]}
                    components={markdownComponents}
                  >
                    {msg.content}
                  </ReactMarkdown>
                </div>
                {msg.role === "assistant" && msg.answerFooter && (
                  <div className="text-xs text-muted-foreground mt-2 pt-2 border-t border-border/60 space-y-1.5">
                    <p>
                      <span className="text-foreground/80">Токены:</span> всего{" "}
                      {formatTokenLine(msg.answerFooter.total_tokens)} · на вход:{" "}
                      {formatTokenLine(msg.answerFooter.prompt_tokens)} · на выход:{" "}
                      {formatTokenLine(msg.answerFooter.completion_tokens)}
                    </p>
                    <p>
                      <span className="text-foreground/80">Время ответа:</span>{" "}
                      {msg.answerFooter.duration_s.toFixed(1)} с
                    </p>
                    <p>
                      <span className="text-foreground/80">Вызовы инструментов:</span>{" "}
                      {msg.answerFooter.tool_calls_count}
                    </p>
                    {msg.answerFooter.log_id ? (
                      <p>
                        <button
                          type="button"
                          className="underline underline-offset-2 text-primary bg-transparent border-0 cursor-pointer p-0 font-inherit text-left"
                          onClick={() =>
                            setSessionLogModalId(msg.answerFooter!.log_id)
                          }
                        >
                          Просмотр лога сессии
                        </button>
                      </p>
                    ) : null}
                  </div>
                )}
              </div>
            </div>
          ))}

          <div ref={scrollRef} />
        </div>
      </ScrollArea>

      <div className="border-t border-border shrink-0">
        <div className="mx-auto w-full max-w-[120ch] px-4 py-4">
          <form onSubmit={handleSubmit} className="flex gap-2">
            <Input
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Спросите о вашем коде…"
              disabled={isStreaming}
              className="flex-1"
            />
            <Button type="submit" disabled={isStreaming || !input.trim()}>
              {isStreaming ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Send className="w-4 h-4" />
              )}
            </Button>
            <Button
              type="button"
              variant="ghost"
              title="Очистить переписку"
              aria-label="Очистить переписку"
              disabled={messages.length === 0}
              onClick={clearChat}
            >
              <Trash2 className="w-4 h-4" />
            </Button>
          </form>
          <p className="text-xs text-muted-foreground mt-2">
            Enter — отправить, Shift+Enter — новая строка
          </p>
        </div>
      </div>

      <SessionLogDialog
        open={sessionLogModalId != null}
        onOpenChange={(open) => {
          if (!open) setSessionLogModalId(null);
        }}
        logId={sessionLogModalId}
      />
    </div>
  );
}
