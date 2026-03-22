/** Отдельное хранилище полных JSON логов сессий (не в localStorage с чатом). */

const DB_NAME = "kpd-codesearch-session-logs";
const DB_VERSION = 1;
const STORE = "sessions";

function openDb(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open(DB_NAME, DB_VERSION);
    req.onerror = () => reject(req.error);
    req.onsuccess = () => resolve(req.result);
    req.onupgradeneeded = () => {
      const db = req.result;
      if (!db.objectStoreNames.contains(STORE)) {
        db.createObjectStore(STORE, { keyPath: "id" });
      }
    };
  });
}

export type SessionLogPayload = Record<string, unknown>;

export interface SessionLogRecord {
  id: string;
  createdAt: number;
  payload: SessionLogPayload;
}

export async function putSessionLog(
  id: string,
  payload: SessionLogPayload
): Promise<void> {
  const db = await openDb();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE, "readwrite");
    tx.oncomplete = () => resolve();
    tx.onerror = () => reject(tx.error);
    const rec: SessionLogRecord = {
      id,
      createdAt: Date.now(),
      payload,
    };
    tx.objectStore(STORE).put(rec);
  });
}

export async function listAllSessionLogs(): Promise<SessionLogRecord[]> {
  const db = await openDb();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE, "readonly");
    const req = tx.objectStore(STORE).getAll();
    req.onerror = () => reject(req.error);
    req.onsuccess = () => {
      const rows = (req.result as SessionLogRecord[]) ?? [];
      rows.sort((a, b) => b.createdAt - a.createdAt);
      resolve(rows);
    };
  });
}

export async function getSessionLog(
  id: string
): Promise<SessionLogPayload | null> {
  const row = await getSessionLogRecord(id);
  return row?.payload ?? null;
}

/** Полная запись для просмотра в UI (id, время, payload). */
export async function getSessionLogRecord(
  id: string
): Promise<SessionLogRecord | null> {
  const db = await openDb();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE, "readonly");
    const req = tx.objectStore(STORE).get(id);
    req.onerror = () => reject(req.error);
    req.onsuccess = () => {
      const row = req.result as SessionLogRecord | undefined;
      resolve(row ?? null);
    };
  });
}

/** Скачать JSON файла с тем же содержимым, что раньше отдавал сервер. */
export async function downloadSessionLogFile(id: string): Promise<void> {
  const payload = await getSessionLog(id);
  if (!payload) return;
  const text = JSON.stringify(payload, null, 2);
  const blob = new Blob([text], { type: "application/json;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  const ts =
    typeof payload.ts === "string"
      ? (payload.ts as string).slice(0, 19).replace(/[:T]/g, "-")
      : String(Date.now());
  a.download = `session_${id.slice(0, 8)}_${ts}.json`;
  a.rel = "noopener";
  a.click();
  URL.revokeObjectURL(url);
}
