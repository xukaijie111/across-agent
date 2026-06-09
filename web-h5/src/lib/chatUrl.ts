export interface ChatUrlState {
  agentId: string;
  sessionId: string;
}

export function parseChatUrl(pathname = window.location.pathname): ChatUrlState {
  const parts = pathname.split("/").filter(Boolean);
  if (parts.length >= 2) {
    return { agentId: parts[0], sessionId: parts[1] };
  }
  if (parts.length === 1) {
    return { agentId: parts[0], sessionId: "" };
  }
  return { agentId: "", sessionId: "" };
}

export function buildChatPath(agentId: string, sessionId: string): string {
  return `/${agentId}/${sessionId}`;
}

export function syncChatUrl(agentId: string, sessionId: string, replace = true): void {
  const next = buildChatPath(agentId, sessionId);
  if (window.location.pathname === next) {
    return;
  }
  if (replace) {
    window.history.replaceState({ agentId, sessionId }, "", next);
  } else {
    window.history.pushState({ agentId, sessionId }, "", next);
  }
}
