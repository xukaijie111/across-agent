export type ContentFormat = "markdown" | "plain";

export type TextEvent = {
  type: "text";
  delta: string;
  format: ContentFormat;
};

export type ToolStartEvent = {
  type: "tool_start";
  id: string;
  name: string;
  args: Record<string, unknown>;
};

export type ToolEndEvent = {
  type: "tool_end";
  id: string;
  result?: string | null;
  error?: string | null;
};

export type ToolConfirmEvent = {
  type: "tool_confirm";
  interruptId: string;
  actionRequests: Array<{
    name: string;
    args: Record<string, unknown>;
  }>;
};

export type ApprovalPendingEvent = { type: "approval_pending" };

export type DoneEvent = { type: "done" };
export type ErrorEvent = { type: "error"; message: string };

export type ChatEvent =
  | TextEvent
  | ToolStartEvent
  | ToolEndEvent
  | ToolConfirmEvent
  | ApprovalPendingEvent
  | DoneEvent
  | ErrorEvent;

export function textEvent(delta: string, format: ContentFormat = "markdown"): TextEvent {
  return { type: "text", delta, format };
}

export function toolStartEvent(
  id: string,
  name: string,
  args: Record<string, unknown>,
): ToolStartEvent {
  return { type: "tool_start", id, name, args };
}

export function toolEndEvent(
  id: string,
  result: string | null,
  error: string | null,
): ToolEndEvent {
  return { type: "tool_end", id, result, error };
}

export function toolConfirmEvent(
  interruptId: string,
  actionRequests: ToolConfirmEvent["actionRequests"],
): ToolConfirmEvent {
  return { type: "tool_confirm", interruptId, actionRequests };
}

export function approvalPendingEvent(): ApprovalPendingEvent {
  return { type: "approval_pending" };
}

export function doneEvent(): DoneEvent {
  return { type: "done" };
}

export function errorEvent(message: string): ErrorEvent {
  return { type: "error", message };
}
