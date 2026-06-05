"use client";

import { useCallback } from "react";
import { Plus, Sparkles } from "lucide-react";

import { AuthPanel } from "@/components/chat/AuthPanel";
import { ChatInput } from "@/components/chat/ChatInput";
import { MessageList } from "@/components/chat/MessageList";
import { ThemeToggle } from "@/components/ThemeToggle";
import { Button } from "@/components/ui/button";
import { useAgentChat } from "@/hooks/useAgentChat";
export function ChatPage() {
  const {
    sessionReady,
    completedTurns,
    streamingTurn,
    isLoading,
    error,
    sendMessage,
    stop,
    clearMessages,
    startNewSession,
  } = useAgentChat();

  const handleAuthChange = useCallback(() => {
    // 登录/退出后重建 session，使 policy 与身份一致
    void startNewSession();
  }, [startNewSession]);

  return (
    <div className="relative flex h-screen flex-col overflow-hidden bg-background">
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 dark:bg-[radial-gradient(ellipse_80%_50%_at_50%_-20%,oklch(0.45_0.15_264/0.18),transparent)]"
      />

      <header className="relative z-10 border-b border-border/60 bg-background/80 backdrop-blur-xl">
        <div className="mx-auto flex h-14 max-w-3xl items-center justify-between px-4 sm:px-6">
          <div className="flex items-center gap-3">
            <div className="flex size-9 items-center justify-center rounded-xl border border-border/60 bg-card shadow-sm">
              <Sparkles className="size-4 text-primary" />
            </div>
            <div>
              <h1 className="text-sm font-semibold tracking-tight">CrossAgent</h1>
              <p className="text-xs text-muted-foreground">
                多端小程序开发助手
                {!sessionReady ? " · 连接中…" : " · 就绪"}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <AuthPanel onAuthChange={handleAuthChange} />
            <ThemeToggle />
            <Button
              variant="outline"
              size="sm"
              onClick={clearMessages}
              className="gap-1.5"
            >
              <Plus className="size-3.5" />
              新会话
            </Button>
          </div>
        </div>
      </header>

      <main className="relative z-10 min-h-0 flex-1">
        <div className="mx-auto h-full max-w-3xl px-4 sm:px-6">
          <MessageList
            completedTurns={completedTurns}
            streamingTurn={streamingTurn}
            isLoading={isLoading}
            onSuggestionClick={sendMessage}
          />
        </div>
      </main>

      <footer className="relative z-10 border-t border-border/60 bg-background/80 backdrop-blur-xl">
        <div className="mx-auto max-w-3xl px-4 py-4 sm:px-6">
          {error ? (
            <div className="mb-3 rounded-lg border border-destructive/30 bg-destructive/10 px-3 py-2 text-sm text-destructive">
              {error}
            </div>
          ) : null}
          <ChatInput
            disabled={!sessionReady || isLoading}
            isLoading={isLoading}
            onSend={sendMessage}
            onStop={stop}
          />
        </div>
      </footer>
    </div>
  );
}
