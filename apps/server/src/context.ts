const MAX_TOOL_CONTENT_CHARS = 2000;
const KEEP_LAST_MESSAGES = 12;

export type ChatMessage = Record<string, unknown>;

function messageChars(msg: ChatMessage): number {
  let n = String(msg.content ?? "").length;
  const toolCalls = (msg.tool_calls as unknown[]) ?? [];
  for (const tc of toolCalls) {
    const row = tc as { function?: { name?: string; arguments?: string } };
    n += (row.function?.name ?? "").length;
    n += (row.function?.arguments ?? "").length;
  }
  return n;
}

function truncateText(text: string, maxChars: number): string {
  if (text.length <= maxChars) return text;
  const half = Math.floor(maxChars / 2) - 24;
  const left = text.slice(0, half);
  const right = text.slice(-half);
  return `${left}\n... [truncated, total ${text.length} chars] ...\n${right}`;
}

function shrinkToolContent(content: string): string {
  if (!content) return content;
  const lower = content.toLowerCase();
  if (["error", "fail", "✗"].some((k) => lower.includes(k))) {
    const lines = content.split("\n");
    const picked: string[] = [];
    picked.push(...lines.slice(0, 5));
    for (const line of lines) {
      if (["error", "fail", "✗"].some((k) => line.toLowerCase().includes(k))) {
        picked.push(line);
      }
    }
    picked.push(...lines.slice(-5));
    const seen = new Set<string>();
    const unique: string[] = [];
    for (const line of picked) {
      if (!seen.has(line)) {
        seen.add(line);
        unique.push(line);
      }
    }
    return truncateText(unique.join("\n"), MAX_TOOL_CONTENT_CHARS);
  }
  return truncateText(content, MAX_TOOL_CONTENT_CHARS);
}

function copyAndShrinkTools(messages: ChatMessage[]): ChatMessage[] {
  return messages.map((msg) => {
    if (msg.role === "tool" && typeof msg.content === "string") {
      return { ...msg, content: shrinkToolContent(msg.content) };
    }
    return { ...msg };
  });
}

export function trimMessages(messages: ChatMessage[]): ChatMessage[] {
  if (!messages.length) return [];
  const systemMsgs = messages.filter((m) => m.role === "system");
  let restMsgs = messages.filter((m) => m.role !== "system");
  if (restMsgs.length > KEEP_LAST_MESSAGES) {
    restMsgs = restMsgs.slice(-KEEP_LAST_MESSAGES);
  }
  return [...systemMsgs, ...copyAndShrinkTools(restMsgs)];
}

export function analyzeMessages(messages: ChatMessage[]) {
  const byRole: Record<string, { count: number; chars: number }> = {};
  for (const msg of messages) {
    const role = String(msg.role ?? "unknown");
    if (!byRole[role]) byRole[role] = { count: 0, chars: 0 };
    byRole[role].count += 1;
    byRole[role].chars += messageChars(msg);
  }
  return {
    total_messages: messages.length,
    total_chars: messages.reduce((sum, m) => sum + messageChars(m), 0),
    by_role: byRole,
  };
}

export function formatAnalysis(analysis: ReturnType<typeof analyzeMessages>): string {
  const lines = [
    `messages=${analysis.total_messages}, chars≈${analysis.total_chars}`,
  ];
  for (const [role, data] of Object.entries(analysis.by_role)) {
    lines.push(`  ${role}: count=${data.count}, chars=${data.chars}`);
  }
  return lines.join("\n");
}
