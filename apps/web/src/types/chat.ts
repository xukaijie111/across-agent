export type MessageRole = "user" | "assistant";

export type ToolStatus = "running" | "success" | "error";

export interface ToolCall {
  id: string;
  name: string;
  args: Record<string, unknown>;
  status: ToolStatus;
  result?: string;
  error?: string;
}

export interface ChatMessage {
  id: string;
  role: MessageRole;
  content: string;
  tools?: ToolCall[];
}

export type ChatEvent =
  | { type: "text"; delta: string }
  | {
      type: "tool_start";
      id: string;
      name: string;
      args: Record<string, unknown>;
    }
  | { type: "tool_end"; id: string; result?: string; error?: string }
  | { type: "done" }
  | { type: "error"; message: string };
