import type { ReactNode } from "react";

/** Разбор отформатированного JSON в узлы с лёгкой подсветкой (без сторонних пакетов). */
export function JsonHighlighter({ text }: { text: string }): ReactNode {
  const nodes: ReactNode[] = [];
  let i = 0;
  let key = 0;

  const push = (s: string, className?: string) => {
    if (!s) return;
    nodes.push(
      <span key={key++} className={className}>
        {s}
      </span>
    );
  };

  while (i < text.length) {
    const c = text[i];

    if (c === '"') {
      let j = i + 1;
      while (j < text.length) {
        if (text[j] === "\\") j += 2;
        else if (text[j] === '"') break;
        else j++;
      }
      const str = text.slice(i, j + 1);
      const after = text.slice(j + 1);
      const isKey = /^\s*:/.test(after);
      push(str, isKey ? "text-primary font-medium" : undefined);
      i = j + 1;
      continue;
    }

    if (/\s/.test(c)) {
      let j = i;
      while (j < text.length && /\s/.test(text[j])) j++;
      push(text.slice(i, j));
      i = j;
      continue;
    }

    if (c === "-" || (c >= "0" && c <= "9")) {
      let j = i;
      if (text[j] === "-") j++;
      while (j < text.length && /[\d.eE+-]/.test(text[j])) j++;
      push(text.slice(i, j), "text-foreground");
      i = j;
      continue;
    }

    if (text.startsWith("true", i)) {
      push("true", "text-muted-foreground");
      i += 4;
      continue;
    }
    if (text.startsWith("false", i)) {
      push("false", "text-muted-foreground");
      i += 5;
      continue;
    }
    if (text.startsWith("null", i)) {
      push("null", "text-muted-foreground");
      i += 4;
      continue;
    }

    push(c, "text-muted-foreground");
    i++;
  }

  return <>{nodes}</>;
}

export function formatPayloadAsJson(payload: Record<string, unknown>): string {
  try {
    return JSON.stringify(payload, null, 2);
  } catch {
    return String(payload);
  }
}
