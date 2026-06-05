import {
  EventSourceMessage,
  fetchEventSource,
} from "@microsoft/fetch-event-source";

import { API_BASE } from "@/lib/api";
import { parseChatEvent, type ChatEvent } from "@/lib/chat-protocol";
import type { SseStreamMeta } from "@/types/sse";

export interface StreamChatHandlers {
  onEvent: (event: ChatEvent) => void;
  /** 每条完整 SSE message（含 data/event/id/retry） */
  onSseMessage?: (message: EventSourceMessage) => void;
  onMeta?: (meta: Partial<SseStreamMeta>) => void;
}

function handleSseMessage(
  message: EventSourceMessage,
  handlers: StreamChatHandlers,
): void {
  handlers.onSseMessage?.(message);

  if (message.id) {
    handlers.onMeta?.({ lastEventId: message.id });
  }
  if (message.event) {
    handlers.onMeta?.({ lastEventName: message.event });
  }
  if (message.retry !== undefined) {
    handlers.onMeta?.({ retryMs: message.retry });
  }

  if (!message.data) return;

  if (message.event && message.event !== "chat") {
    return;
  }

  const event = parseChatEvent(JSON.parse(message.data));
  handlers.onEvent(event);
}

export async function streamChat(
  sessionId: string,
  message: string,
  handlers: StreamChatHandlers,
  signal?: AbortSignal,
): Promise<void> {
  await fetchEventSource(`${API_BASE}/chat/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      session_id: sessionId,
      message,
    }),
    signal,
    openWhenHidden: true,
    onmessage(message) {
      try {
        handleSseMessage(message, handlers);
      } catch (err) {
        const msg = err instanceof Error ? err.message : "SSE parse failed";
        handlers.onEvent({ type: "error", message: msg });
        throw err;
      }
    },
    onclose() {
      // 流正常结束
    },
    onerror(err) {
      throw err;
    },
  });
}
