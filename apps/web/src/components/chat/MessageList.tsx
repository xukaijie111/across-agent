"use client";

import { useEffect, useRef } from "react";
import { Code2, FileSearch, MessageSquare, Wrench } from "lucide-react";

import { TurnBubble } from "@/components/chat/TurnBubble";
import { TypingIndicator } from "@/components/chat/TypingIndicator";
import { ScrollArea } from "@/components/ui/scroll-area";
import type { ChatTurn } from "@/lib/chat-protocol";

interface MessageListProps {
  completedTurns: ChatTurn[];
  streamingTurn: ChatTurn | null;
  isLoading: boolean;
  onSuggestionClick?: (text: string) => void;
}

const SUGGESTIONS = [
  { icon: MessageSquare, text: "检测项目用的是哪个框架" },
  { icon: FileSearch, text: "帮我排查构建报错" },
  { icon: Code2, text: "分析 pages.json 配置" },
  { icon: Wrench, text: "读一下 package.json" },
];

export function MessageList({
  completedTurns,
  streamingTurn,
  isLoading,
  onSuggestionClick,
}: MessageListProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [completedTurns, streamingTurn, isLoading]);

  const isEmpty = completedTurns.length === 0 && !streamingTurn;

  if (isEmpty) {
    return (
      <div className="flex h-full flex-col items-center justify-center px-4 py-12 text-center">
        <div className="mb-6 flex size-14 items-center justify-center rounded-2xl border border-border/60 bg-card shadow-sm">
          <MessageSquare className="size-6 text-primary" />
        </div>
        <h2 className="text-xl font-semibold tracking-tight">
          有什么可以帮你的？
        </h2>
        <p className="mt-2 max-w-md text-sm leading-6 text-muted-foreground">
          熟悉 uni-app、Taro、Morjs，可以帮你检测框架、排查构建、分析配置、修改代码。
        </p>
        {onSuggestionClick ? (
          <div className="mt-8 grid w-full max-w-lg gap-2 sm:grid-cols-2">
            {SUGGESTIONS.map(({ icon: Icon, text }) => (
              <button
                key={text}
                type="button"
                onClick={() => onSuggestionClick(text)}
                className="flex items-start gap-3 rounded-xl border border-border/60 bg-card/50 px-4 py-3 text-left text-sm transition-colors hover:border-primary/40 hover:bg-card"
              >
                <Icon className="mt-0.5 size-4 shrink-0 text-muted-foreground" />
                <span className="leading-5 text-foreground/90">{text}</span>
              </button>
            ))}
          </div>
        ) : null}
      </div>
    );
  }

  const showTyping =
    isLoading &&
    (!streamingTurn || streamingTurn.assistant.contents.length === 0);

  return (
    <ScrollArea className="h-full">
      <div className="space-y-8 py-6">
        {completedTurns.map((turn) => (
          <TurnBubble key={turn.id} turn={turn} />
        ))}
        {streamingTurn ? (
          <TurnBubble key={`streaming-${streamingTurn.id}`} turn={streamingTurn} />
        ) : null}
        {showTyping ? <TypingIndicator /> : null}
        <div ref={bottomRef} />
      </div>
    </ScrollArea>
  );
}
