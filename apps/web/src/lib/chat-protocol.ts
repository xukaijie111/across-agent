/**
 * CrossAgent 聊天协议 — 与后端 apps/server/src/graph/chatEvents.ts 对齐。
 *
 * UI 会话结构：turns[]，每轮 { user, assistant: { contents[] } }。
 * 流式事件按到达顺序写入最后一轮的 assistant.contents，渲染 contents.map，不调序。
 */

export type MessageRole = "user" | "assistant";

export type ToolStatus = "running" | "success" | "error";

export type TextPart = {
  type: "text";
  content: string;
};

export type ToolPart = {
  type: "tool";
  id: string;
  name: string;
  args: Record<string, unknown>;
  status: ToolStatus;
  result?: string;
  error?: string;
};

export type MessagePart = TextPart | ToolPart;

/** @deprecated 使用 ToolPart */
export type ToolCall = ToolPart;

export interface UserTurnSide {
  content: string;
}

export interface AssistantTurnSide {
  contents: MessagePart[];
}

/** 一轮对话：用户提问 + 助手回复（含 tool / 正文，有序） */
export interface ChatTurn {
  id: string;
  user: UserTurnSide;
  assistant: AssistantTurnSide;
}

export type ChatEvent =
  | { type: "text"; delta: string; format?: ContentFormat }
  | {
      type: "tool_start";
      id: string;
      name: string;
      args: Record<string, unknown>;
    }
  | { type: "tool_end"; id: string; result?: string; error?: string }
  | { type: "done" }
  | { type: "error"; message: string };

/** 历史 API 扁平条目（POST /session/histroy） */
export interface HistoryMessage {
  role: MessageRole;
  content: string;
}

/** SSE text 事件可能携带；UI 按 role 渲染，不依赖此字段 */
export type ContentFormat = "markdown" | "plain";

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

export function parseChatEvent(raw: unknown): ChatEvent {
  if (!isRecord(raw) || typeof raw.type !== "string") {
    throw new Error("invalid chat event");
  }

  switch (raw.type) {
    case "text": {
      if (typeof raw.delta !== "string") {
        throw new Error("text event missing delta");
      }
      return { type: "text", delta: raw.delta };
    }
    case "tool_start": {
      if (
        typeof raw.id !== "string" ||
        typeof raw.name !== "string" ||
        !isRecord(raw.args)
      ) {
        throw new Error("invalid tool_start event");
      }
      return {
        type: "tool_start",
        id: raw.id,
        name: raw.name,
        args: raw.args,
      };
    }
    case "tool_end": {
      if (typeof raw.id !== "string") {
        throw new Error("invalid tool_end event");
      }
      return {
        type: "tool_end",
        id: raw.id,
        result: typeof raw.result === "string" ? raw.result : undefined,
        error: typeof raw.error === "string" ? raw.error : undefined,
      };
    }
    case "done":
      return { type: "done" };
    case "error": {
      if (typeof raw.message !== "string") {
        throw new Error("invalid error event");
      }
      return { type: "error", message: raw.message };
    }
    default:
      throw new Error(`unknown chat event type: ${raw.type}`);
  }
}

function createTurnId(): string {
  return crypto.randomUUID();
}

function appendTextPart(parts: MessagePart[], delta: string): MessagePart[] {
  if (!delta) return parts;
  const last = parts[parts.length - 1];
  if (last?.type === "text") {
    return [
      ...parts.slice(0, -1),
      { type: "text", content: last.content + delta },
    ];
  }
  return [...parts, { type: "text", content: delta }];
}

function updateLastTurn(
  turns: ChatTurn[],
  updater: (turn: ChatTurn) => ChatTurn,
): ChatTurn[] {
  if (turns.length === 0) return turns;
  const last = turns[turns.length - 1];
  return [...turns.slice(0, -1), updater(last)];
}

export function createTurn(userContent: string): ChatTurn {
  return {
    id: createTurnId(),
    user: { content: userContent },
    assistant: { contents: [] },
  };
}

/** 将 SSE 事件写入单轮 assistant.contents（流式当前轮） */
export function applyChatEventToTurn(turn: ChatTurn, event: ChatEvent): ChatTurn {
  if (event.type === "text") {
    return {
      ...turn,
      assistant: {
        contents: appendTextPart(turn.assistant.contents, event.delta),
      },
    };
  }

  if (event.type === "tool_start") {
    if (
      turn.assistant.contents.some(
        (part) => part.type === "tool" && part.id === event.id,
      )
    ) {
      return turn;
    }
    const tool: ToolPart = {
      type: "tool",
      id: event.id,
      name: event.name,
      args: event.args,
      status: "running",
    };
    return {
      ...turn,
      assistant: {
        contents: [...turn.assistant.contents, tool],
      },
    };
  }

  if (event.type === "tool_end") {
    return {
      ...turn,
      assistant: {
        contents: turn.assistant.contents.map((part) =>
          part.type === "tool" && part.id === event.id
            ? {
                ...part,
                status: event.error ? ("error" as const) : ("success" as const),
                result: event.result,
                error: event.error,
              }
            : part,
        ),
      },
    };
  }

  return turn;
}

/** @deprecated 流式请用 applyChatEventToTurn + streamingTurn */
export function applyChatEvent(turns: ChatTurn[], event: ChatEvent): ChatTurn[] {
  if (turns.length === 0) return turns;
  return updateLastTurn(turns, (turn) => applyChatEventToTurn(turn, event));
}

/** 历史 API 扁平列表 → 按轮分组 */
export function historyToTurns(rows: HistoryMessage[]): ChatTurn[] {
  const turns: ChatTurn[] = [];
  let pendingUser: string | null = null;

  const flushUserOnly = () => {
    if (pendingUser === null) return;
    turns.push({
      id: createTurnId(),
      user: { content: pendingUser },
      assistant: { contents: [] },
    });
    pendingUser = null;
  };

  for (const row of rows) {
    if (row.role === "user") {
      flushUserOnly();
      pendingUser = row.content;
      continue;
    }

    if (row.role === "assistant") {
      const userContent = pendingUser ?? "";
      pendingUser = null;
      turns.push({
        id: createTurnId(),
        user: { content: userContent },
        assistant: {
          contents: row.content
            ? [{ type: "text", content: row.content }]
            : [],
        },
      });
    }
  }

  flushUserOnly();
  return turns;
}
