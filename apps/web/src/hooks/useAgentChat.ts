"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { flushSync } from "react-dom";

import {
  applyChatEventToTurn,
  createTurn,
  type ChatTurn,
} from "@/lib/chat-protocol";
import {
  createSession,
  fetchSessionMessages,
  getSessionIdFromUrl,
  setSessionIdInUrl,
  toChatTurns,
} from "@/lib/session";
import { streamChat } from "@/lib/sse";
import type { SseStreamMeta } from "@/types/sse";

export function useAgentChat() {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [sessionReady, setSessionReady] = useState(false);
  const [completedTurns, setCompletedTurns] = useState<ChatTurn[]>([]);
  const [streamingTurn, setStreamingTurn] = useState<ChatTurn | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [sseMeta, setSseMeta] = useState<SseStreamMeta>({
    lastEventId: "",
    lastEventName: "",
  });
  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function initSession() {
      try {
        const fromUrl = getSessionIdFromUrl();

        if (fromUrl) {
          const history = await fetchSessionMessages(fromUrl);
          if (cancelled) return;
          setSessionId(fromUrl);
          setCompletedTurns(toChatTurns(history));
          setStreamingTurn(null);
          setSessionReady(true);
          return;
        }

        const id = await createSession();
        if (cancelled) return;
        setSessionId(id);
        setCompletedTurns([]);
        setStreamingTurn(null);
        setSessionIdInUrl(id);
        setSessionReady(true);
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "session init failed");
          setSessionReady(true);
        }
      }
    }

    void initSession();

    return () => {
      cancelled = true;
    };
  }, []);

  const stop = useCallback(() => {
    abortRef.current?.abort();
    abortRef.current = null;
    setIsLoading(false);
  }, []);

  const startNewSession = useCallback(async () => {
    stop();
    setError(null);
    const id = await createSession();
    setSessionId(id);
    setCompletedTurns([]);
    setStreamingTurn(null);
    setSessionIdInUrl(id);
  }, [stop]);

  const sendMessage = useCallback(
    async (content: string) => {
      const text = content.trim();
      if (!text || isLoading || !sessionId || !sessionReady) return;

      flushSync(() => {
        setStreamingTurn(createTurn(text));
      });
      setIsLoading(true);
      setError(null);
      setSseMeta({ lastEventId: "", lastEventName: "" });

      const controller = new AbortController();
      abortRef.current = controller;

      try {
        await streamChat(
          sessionId,
          text,
          {
            onEvent: (event) => {
              if (event.type === "error") {
                setError(event.message);
                return;
              }
              if (event.type === "done") {
                // 原子并入 completed，避免同一 turn.id 同时出现在两列表导致 React key 冲突
                flushSync(() => {
                  setStreamingTurn((turn) => {
                    if (turn) {
                      setCompletedTurns((completed) =>
                        completed.some((t) => t.id === turn.id)
                          ? completed
                          : [...completed, turn],
                      );
                    }
                    return null;
                  });
                });
                return;
              }
              setStreamingTurn((turn) =>
                turn ? applyChatEventToTurn(turn, event) : turn,
              );
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
            err instanceof Error ? err.message : "请求失败，请确认 API 已启动";
          setError(message);
        }
      } finally {
        abortRef.current = null;
        setIsLoading(false);
      }
    },
    [isLoading, sessionId, sessionReady],
  );

  const clearMessages = useCallback(() => {
    void startNewSession();
  }, [startNewSession]);

  const turns = streamingTurn
    ? [...completedTurns, streamingTurn]
    : completedTurns;

  return {
    sessionId,
    sessionReady,
    completedTurns,
    streamingTurn,
    turns,
    isLoading,
    error,
    sseMeta,
    sendMessage,
    stop,
    clearMessages,
    startNewSession,
  };
}
