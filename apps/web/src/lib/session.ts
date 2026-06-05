import { API_BASE } from "@/lib/api";
import type { ChatTurn, HistoryMessage } from "@/lib/chat-protocol";
import { historyToTurns } from "@/lib/chat-protocol";

export const SESSION_QUERY_KEY = "session";

export function getSessionIdFromUrl(): string | null {
  if (typeof window === "undefined") return null;
  return new URLSearchParams(window.location.search).get(SESSION_QUERY_KEY);
}

export function setSessionIdInUrl(sessionId: string) {
  const url = new URL(window.location.href);
  url.searchParams.set(SESSION_QUERY_KEY, sessionId);
  window.history.replaceState(null, "", url.toString());
}

export async function createSession(): Promise<string> {
  const res = await fetch(`${API_BASE}/session/create`, { method: "POST" });
  if (!res.ok) {
    throw new Error("create session failed");
  }
  const data = (await res.json()) as { session_id: string };
  return data.session_id;
}

/** 与后端 POST /session/histroy 对齐（后端路径拼写暂保留） */
export async function fetchSessionMessages(
  sessionId: string,
): Promise<HistoryMessage[]> {
  const url = new URL(`${API_BASE}/session/histroy`);
  url.searchParams.set("session_id", sessionId);
  const res = await fetch(url.toString(), { method: "POST" });
  if (!res.ok) {
    throw new Error("load session history failed");
  }
  const rows = (await res.json()) as HistoryMessage[];
  return rows.filter(
    (m) =>
      (m.role === "user" || m.role === "assistant") &&
      typeof m.content === "string",
  );
}

export function toChatTurns(rows: HistoryMessage[]): ChatTurn[] {
  return historyToTurns(rows);
}
