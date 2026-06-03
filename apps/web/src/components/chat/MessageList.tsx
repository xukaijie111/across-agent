"use client";

import { useEffect, useRef } from "react";

import { MessageBubble } from "@/components/chat/MessageBubble";
import { ScrollArea } from "@/components/ui/scroll-area";
import type { ChatMessage } from "@/types/chat";

interface MessageListProps {
  messages: ChatMessage[];
  isLoading: boolean;
}

export function MessageList({ messages, isLoading }: MessageListProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isLoading]);

  if (messages.length === 0) {
    return (
      <div className="flex h-full items-center justify-center px-6 text-center text-sm text-muted-foreground">
        发送消息开始对话。开发环境已接 mock SSE。
        <br />
        试「你好」流式回复，或「读文件 / tool」看 Tool 卡片。
      </div>
    );
  }

  return (
    <ScrollArea className="h-full pr-3">
      <div className="space-y-4 pb-4">
        {messages.map((message) => (
          <MessageBubble key={message.id} message={message} />
        ))}
        {isLoading ? (
          <div className="text-xs text-muted-foreground">Agent 思考中...</div>
        ) : null}
        <div ref={bottomRef} />
      </div>
    </ScrollArea>
  );
}
