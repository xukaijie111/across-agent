import {
  EventSourceMessage,
  fetchEventSource,
} from "@microsoft/fetch-event-source";

import { API_BASE } from "@/lib/api";
import type { ChatEvent, ChatMessage } from "@/types/chat";
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

  // event 字段：默认 chat；ping 等控制类事件跳过业务 parse
  if (message.event && message.event !== "chat") {
    return;
  }

  const event = JSON.parse(message.data) as ChatEvent;
  handlers.onEvent(event);
}

export async function streamChat(
  messages: ChatMessage[],
  handlers: StreamChatHandlers,
  signal?: AbortSignal,
): Promise<void> {
  await fetchEventSource(`${API_BASE}/chat/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      messages: messages.map(({ role, content }) => ({ role, content })),
    }),
    signal,
    openWhenHidden: true,
    onmessage(message) {
      console.error(`message is`,message,typeof message);
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
      // 聊天场景不自动重连；抛出让 Promise reject
      throw err;
    },
  });
}
