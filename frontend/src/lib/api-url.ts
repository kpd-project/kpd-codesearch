/**
 * База API: пусто = относительные URL (тот же хост, Vite proxy в dev).
 * Для прямого вызова бэкенда: VITE_API_BASE_URL=http://127.0.0.1:8000
 */
export function apiUrl(path: string): string {
  const raw = import.meta.env.VITE_API_BASE_URL as string | undefined;
  const base = raw?.trim().replace(/\/$/, "") ?? "";
  if (!base) return path.startsWith("/") ? path : `/${path}`;
  return `${base}${path.startsWith("/") ? path : `/${path}`}`;
}
