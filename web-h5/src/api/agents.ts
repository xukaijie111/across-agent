import type { AgentInfo, HistoryMessage, SessionDetail, SessionSummary } from "../types";

export async function fetchAgents(): Promise<AgentInfo[]> {
  const res = await fetch("/api/agents");
  if (!res.ok) {
    throw new Error(`加载 Agent 列表失败: ${res.status}`);
  }
  return res.json();
}

export async function fetchSession(sessionId: string): Promise<SessionDetail> {
  const res = await fetch(`/api/sessions/${sessionId}`);
  if (!res.ok) {
    throw new Error(`会话不存在: ${res.status}`);
  }
  return res.json();
}

export async function createSession(
  agentId: string,
  resumeSessionId?: string,
): Promise<{ session_id: string; agent_id: string; resumed: boolean }> {
  const res = await fetch("/api/sessions", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      agent_id: agentId,
      resume_session_id: resumeSessionId || null,
    }),
  });
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(detail || `创建会话失败: ${res.status}`);
  }
  return res.json();
}

export async function fetchSessionMessages(sessionId: string): Promise<HistoryMessage[]> {
  const res = await fetch(`/api/sessions/${sessionId}/messages`);
  if (!res.ok) {
    return [];
  }
  return res.json();
}

export async function fetchSessions(agentId: string): Promise<SessionSummary[]> {
  const res = await fetch(`/api/sessions?agent_id=${encodeURIComponent(agentId)}`);
  if (!res.ok) {
    return [];
  }
  return res.json();
}

export async function resetSession(sessionId: string): Promise<void> {
  const res = await fetch(`/api/sessions/${sessionId}/reset`, { method: "POST" });
  if (!res.ok) {
    throw new Error(`重置会话失败: ${res.status}`);
  }
}

export function sessionStorageKey(agentId: string): string {
  return `agent_session_${agentId}`;
}

export function readStoredSessionId(agentId: string): string | null {
  return localStorage.getItem(sessionStorageKey(agentId));
}

export function writeStoredSessionId(agentId: string, sessionId: string): void {
  localStorage.setItem(sessionStorageKey(agentId), sessionId);
}

export function clearStoredSessionId(agentId: string): void {
  localStorage.removeItem(sessionStorageKey(agentId));
}
