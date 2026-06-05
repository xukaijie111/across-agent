import { parseToolPolicy, type ToolPolicy } from "../tools/policy.js";

/** SSE 流式回调，经 LangGraph configurable 传入节点 */
export interface StreamCallbacks {
  onTextDelta?: (delta: string) => void;
  onToolStart?: (id: string, name: string, args: Record<string, unknown>) => void;
}

export type ThreadConfigurable = {
  thread_id: string;
  toolPolicy?: ToolPolicy;
  onTextDelta?: (delta: string) => void;
  onToolStart?: (id: string, name: string, args: Record<string, unknown>) => void;
};

function isTextDeltaHandler(value: unknown): value is (delta: string) => void {
  return typeof value === "function";
}

function isToolStartHandler(
  value: unknown,
): value is (id: string, name: string, args: Record<string, unknown>) => void {
  return typeof value === "function";
}

export function getStreamCallbacks(
  configurable: Record<string, unknown> | undefined,
): StreamCallbacks {
  const onTextDelta = configurable?.onTextDelta;
  const onToolStart = configurable?.onToolStart;
  return {
    onTextDelta: isTextDeltaHandler(onTextDelta) ? onTextDelta : undefined,
    onToolStart: isToolStartHandler(onToolStart) ? onToolStart : undefined,
  };
}

export function getToolPolicy(
  configurable: Record<string, unknown> | undefined,
): ToolPolicy {
  return parseToolPolicy(configurable?.toolPolicy);
}
