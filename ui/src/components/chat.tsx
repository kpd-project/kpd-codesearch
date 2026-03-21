import { useState, useRef, useEffect } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type { Components } from "react-markdown";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Send, Trash2, Loader2, Bot } from "lucide-react";
import { cn } from "@/lib/utils";

interface Message {
  role: "user" | "assistant";
  content: string;
}

/** Один локальный чат; версия ключа — при смене формата данных. */
const CHAT_STORAGE_KEY = "kpd-codesearch-chat-messages-v1";

function loadMessagesFromStorage(): Message[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = localStorage.getItem(CHAT_STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw) as unknown;
    if (!Array.isArray(parsed)) return [];
    return parsed.filter(
      (m): m is Message =>
        m != null &&
        typeof m === "object" &&
        ((m as Message).role === "user" ||
          (m as Message).role === "assistant") &&
        typeof (m as Message).content === "string"
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

      setMessages((prev) => [...prev, { role: "assistant", content: "" }]);

      const appendToAssistant = (delta: string) => {
        setMessages((prev) => {
          const last = prev[prev.length - 1];
          if (last?.role === "assistant") {
            return [
              ...prev.slice(0, -1),
              { ...last, content: last.content + delta },
            ];
          }
          return prev;
        });
      };

      const consumeSsePayload = (payload: string) => {
        if (payload === "[DONE]") return;
        try {
          const parsed = JSON.parse(payload) as {
            content?: string;
            error?: string;
          };
          if (parsed.error) {
            appendToAssistant(`\n\nОшибка: ${parsed.error}`);
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
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: "Ошибка: не удалось получить ответ" },
      ]);
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
                <div
                  className={cn(
                    "prose prose-lg max-w-none break-words [&_pre]:max-w-full [&_pre]:overflow-x-auto",
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
              </div>
            </div>
          ))}

          {isStreaming && (
            <div className="flex justify-start">
              <div className="rounded-tl-2xl rounded-tr-2xl rounded-br-2xl rounded-bl-none bg-muted text-foreground p-4 w-fit min-w-[min(100%,12rem)] max-w-full flex items-center gap-2">
                <Bot className="h-4 w-4 shrink-0 text-muted-foreground" aria-hidden />
                <Loader2 className="w-4 h-4 animate-spin shrink-0" />
              </div>
            </div>
          )}

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
    </div>
  );
}
