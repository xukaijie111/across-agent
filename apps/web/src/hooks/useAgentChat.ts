"use client";

import { useCallback, useRef, useState } from "react";
import { flushSync } from "react-dom";

import { streamChat } from "@/lib/sse";
import type { ChatEvent, ChatMessage, ToolCall } from "@/types/chat";
import type { SseStreamMeta } from "@/types/sse";

function createId() {
  return crypto.randomUUID();
}

function applyEvent(messages: ChatMessage[], event: ChatEvent): ChatMessage[] {
  if (event.type === "text") {
    const last = messages[messages.length - 1];
    if (last?.role === "assistant") {
      return [
        ...messages.slice(0, -1),
        { ...last, content: last.content + event.delta },
      ];
    }
    return [
      ...messages,
      { id: createId(), role: "assistant", content: event.delta, tools: [] },
    ];
  }

  if (event.type === "tool_start") {
    const last = messages[messages.length - 1];
    const tool: ToolCall = {
      id: event.id,
      name: event.name,
      args: event.args,
      status: "running",
    };
    if (last?.role === "assistant") {
      return [
        ...messages.slice(0, -1),
        { ...last, tools: [...(last.tools ?? []), tool] },
      ];
    }
    return [
      ...messages,
      { id: createId(), role: "assistant", content: "", tools: [tool] },
    ];
  }

  if (event.type === "tool_end") {
    const last = messages[messages.length - 1];
    if (last?.role !== "assistant") return messages;
    const tools = (last.tools ?? []).map((tool) =>
      tool.id === event.id
        ? {
            ...tool,
            status: event.error ? ("error" as const) : ("success" as const),
            result: event.result,
            error: event.error,
          }
        : tool,
    );
    return [...messages.slice(0, -1), { ...last, tools }];
  }

  return messages;
}

export function useAgentChat() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [sseMeta, setSseMeta] = useState<SseStreamMeta>({
    lastEventId: "",
    lastEventName: "",
  });
  const abortRef = useRef<AbortController | null>(null);

  const stop = useCallback(() => {
    abortRef.current?.abort();
    abortRef.current = null;
    setIsLoading(false);
  }, []);

  const sendMessage = useCallback(
    async (content: string) => {
      const text = content.trim();
      if (!text || isLoading) return;

      const userMessage: ChatMessage = {
        id: createId(),
        role: "user",
        content: text,
      };
      const history = [...messages, userMessage];

      flushSync(() => {
        setMessages(history);
      });
      setIsLoading(true);
      setError(null);
      setSseMeta({ lastEventId: "", lastEventName: "" });

      const controller = new AbortController();
      abortRef.current = controller;

      try {
        await streamChat(
          history,
          {
            onEvent: (event) => {
              if (event.type === "error") {
                setError(event.message);
                return;
              }
              if (event.type === "done") {
                return;
              }
              setMessages((current) => applyEvent(current, event));
            },
            onMeta: (meta) => {
              setSseMeta((prev) => ({ ...prev, ...meta }));
            },
          },
          controller.signal,
        );
      } catch (err) {
        if (!(err instanceof Error && err.name === "AbortError")) {
          const message =
            err instanceof Error ? err.message : "请求失败，请确认 FastAPI 已启动";
          setError(message);
        }
      } finally {
        abortRef.current = null;
        setIsLoading(false);
      }
    },
    [isLoading, messages],
  );

  const clearMessages = useCallback(() => {
    stop();
    setMessages([]);
    setError(null);
  }, [stop]);

  return {
    messages,
    isLoading,
    error,
    sseMeta,
    sendMessage,
    stop,
    clearMessages,
  };
}
