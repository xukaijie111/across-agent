"use client";

import { ChatInput } from "@/components/chat/ChatInput";
import { MessageList } from "@/components/chat/MessageList";
import { Button } from "@/components/ui/button";
import { useAgentChat } from "@/hooks/useAgentChat";
import { API_BASE, IS_MOCK } from "@/lib/api";

export function ChatPage() {
  const { messages, isLoading, error, sseMeta, sendMessage, stop, clearMessages } =
    useAgentChat();

  return (
    <div className="mx-auto flex h-screen max-w-4xl flex-col">
      <header className="flex items-center justify-between border-b px-4 py-3">
        <div>
          <h1 className="text-lg font-semibold">CrossAgent</h1>
          <p className="text-xs text-muted-foreground">
            API: {API_BASE}
            {IS_MOCK ? " (mock)" : ""}
            {sseMeta.lastEventId
              ? ` · id:${sseMeta.lastEventId}`
              : null}
            {sseMeta.lastEventName
              ? ` · event:${sseMeta.lastEventName}`
              : null}
            {sseMeta.retryMs !== undefined
              ? ` · retry:${sseMeta.retryMs}ms`
              : null}
          </p>
        </div>
        <Button variant="outline" size="sm" onClick={clearMessages}>
          清空
        </Button>
      </header>

      <main className="min-h-0 flex-1 px-4 py-4">
        <MessageList messages={messages} isLoading={isLoading} />
        {error ? (
          <div className="mt-3 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
            {error}
          </div>
        ) : null}
      </main>

      <ChatInput
        disabled={isLoading}
        isLoading={isLoading}
        onSend={sendMessage}
        onStop={stop}
      />
    </div>
  );
}
