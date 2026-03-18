import { useState, useRef, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Send, Trash2, Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";

interface Message {
  role: "user" | "assistant";
  content: string;
}

interface ChatProps {
  className?: string;
}

export function Chat({ className }: ChatProps) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    scrollRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

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
      
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const text = new TextDecoder().decode(value);
        const lines = text.split("\n");

        for (const line of lines) {
          if (line.startsWith("data: ")) {
            const data = line.slice(6);
            if (data === "[DONE]") continue;
            
            try {
              const parsed = JSON.parse(data);
              if (parsed.content) {
                setMessages((prev) => {
                  const last = prev[prev.length - 1];
                  if (last?.role === "assistant") {
                    return [...prev.slice(0, -1), { ...last, content: last.content + parsed.content }];
                  }
                  return prev;
                });
              }
            } catch {
              // Raw text
              setMessages((prev) => {
                const last = prev[prev.length - 1];
                if (last?.role === "assistant") {
                  return [...prev.slice(0, -1), { ...last, content: last.content + data }];
                }
                return prev;
              });
            }
          }
        }
      }
    } catch (error) {
      console.error("Query error:", error);
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: "Error: Failed to get response" },
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
      <ScrollArea className="flex-1 p-4">
        <div className="space-y-4">
          {messages.length === 0 && (
            <div className="text-center text-slate-500 mt-20">
              <p>Ask me anything about your code!</p>
              <p className="text-sm mt-2">
                Example: "How does authentication work?"
              </p>
            </div>
          )}
          
          {messages.map((msg, i) => (
            <div
              key={i}
              className={cn(
                "rounded-lg p-4",
                msg.role === "user"
                  ? "bg-blue-600 text-white ml-12"
                  : "bg-slate-800 text-slate-100 mr-12"
              )}
            >
              <div className="font-semibold text-xs mb-1 opacity-70">
                {msg.role === "user" ? "You" : "Assistant"}
              </div>
              <div className="whitespace-pre-wrap prose prose-sm max-w-none dark:prose-invert">
                {msg.content}
              </div>
            </div>
          ))}
          
          {isStreaming && (
            <div className="bg-slate-800 text-slate-100 rounded-lg p-4 mr-12">
              <Loader2 className="w-4 h-4 animate-spin" />
            </div>
          )}
          
          <div ref={scrollRef} />
        </div>
      </ScrollArea>

      <div className="p-4 border-t border-slate-800">
        <form onSubmit={handleSubmit} className="flex gap-2">
          <Input
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask about your code..."
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
          <Button type="button" variant="ghost" onClick={clearChat}>
            <Trash2 className="w-4 h-4" />
          </Button>
        </form>
        <p className="text-xs text-slate-500 mt-2">
          Press Enter to send, Shift+Enter for newline
        </p>
      </div>
    </div>
  );
}
