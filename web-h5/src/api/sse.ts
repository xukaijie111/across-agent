import { getUserId } from "../lib/userId";
import type { SseHandler } from "../types";

function parseSseBlock(block: string): { event: string; data: string } | null {
  const lines = block.split("\n");
  let event = "message";
  const dataLines: string[] = [];
  for (const line of lines) {
    if (line.startsWith("event:")) {
      event = line.slice(6).trim();
    } else if (line.startsWith("data:")) {
      dataLines.push(line.slice(5).trim());
    }
  }
  if (dataLines.length === 0) {
    return null;
  }
  return { event, data: dataLines.join("\n") };
}

async function consumeSseResponse(res: Response, onEvent: SseHandler, signal?: AbortSignal): Promise<void> {
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(detail || `请求失败: ${res.status}`);
  }
  if (!res.body) {
    throw new Error("浏览器不支持流式响应");
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    if (signal?.aborted) {
      await reader.cancel();
      return;
    }
    const { done, value } = await reader.read();
    if (done) {
      break;
    }
    buffer += decoder.decode(value, { stream: true });
    const parts = buffer.split("\n\n");
    buffer = parts.pop() ?? "";
    for (const part of parts) {
      const parsed = parseSseBlock(part.trim());
      if (!parsed) {
        continue;
      }
      let payload: Record<string, unknown> = {};
      try {
        payload = JSON.parse(parsed.data) as Record<string, unknown>;
      } catch {
        payload = { raw: parsed.data };
      }
      onEvent(parsed.event, payload);
    }
  }
}

export async function streamChat(
  sessionId: string,
  message: string,
  onEvent: SseHandler,
  signal?: AbortSignal,
): Promise<void> {
  const res = await fetch("/api/chat/stream", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: sessionId, user_id: getUserId(), message }),
    signal,
  });
  await consumeSseResponse(res, onEvent, signal);
}

export async function streamResume(
  sessionId: string,
  decision: "confirm" | "cancel",
  onEvent: SseHandler,
  signal?: AbortSignal,
): Promise<void> {
  const res = await fetch("/api/chat/resume", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: sessionId, user_id: getUserId(), decision }),
    signal,
  });
  await consumeSseResponse(res, onEvent, signal);
}
