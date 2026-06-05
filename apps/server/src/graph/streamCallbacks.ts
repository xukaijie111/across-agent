/** SSE 流式回调，经 LangGraph configurable 传入 callModel */
export interface StreamCallbacks {
  onTextDelta?: (delta: string) => void;
}

export type ThreadConfigurable = {
  thread_id: string;
  onTextDelta?: (delta: string) => void;
};

function isTextDeltaHandler(value: unknown): value is (delta: string) => void {
  return typeof value === "function";
}

export function getStreamCallbacks(
  configurable: Record<string, unknown> | undefined,
): StreamCallbacks {
  const onTextDelta = configurable?.onTextDelta;
  return {
    onTextDelta: isTextDeltaHandler(onTextDelta) ? onTextDelta : undefined,
  };
}
