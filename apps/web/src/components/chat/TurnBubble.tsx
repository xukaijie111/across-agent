import { memo } from "react";
import { Bot, User } from "lucide-react";

import { MessageContent } from "@/components/chat/MessageContent";
import { ToolCard } from "@/components/chat/ToolCard";
import type { ChatTurn } from "@/lib/chat-protocol";

interface TurnBubbleProps {
  turn: ChatTurn;
}

function TurnBubbleInner({ turn }: TurnBubbleProps) {
  const { user, assistant } = turn;

  return (
    <div className="space-y-6">
      {user.content ? (
        <div className="group flex flex-row-reverse gap-3">
          <div className="flex size-8 shrink-0 items-center justify-center rounded-lg border border-primary/30 bg-primary/15 text-primary">
            <User className="size-4" />
          </div>
          <div className="max-w-[min(100%,36rem)] min-w-0">
            <div className="rounded-2xl bg-primary px-4 py-3 text-primary-foreground">
              <MessageContent role="user" content={user.content} />
            </div>
          </div>
        </div>
      ) : null}

      {assistant.contents.length > 0 ? (
        <div className="group flex gap-3">
          <div className="flex size-8 shrink-0 items-center justify-center rounded-lg border border-border/60 bg-card text-muted-foreground">
            <Bot className="size-4" />
          </div>
          <div className="min-w-0 flex-1 space-y-2">
            {assistant.contents.map((part, index) => {
              if (part.type === "text") {
                if (!part.content) return null;
                return (
                  <div key={`text-${index}`} className="py-1 pr-2">
                    <MessageContent role="assistant" content={part.content} />
                  </div>
                );
              }
              return <ToolCard key={part.id} tool={part} />;
            })}
          </div>
        </div>
      ) : null}
    </div>
  );
}

/** 已完成轮次：props 引用不变时不重渲染（配合高频 text delta） */
export const TurnBubble = memo(TurnBubbleInner);
