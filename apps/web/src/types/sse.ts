/** SSE 传输层元信息（id / event / retry） */
export interface SseStreamMeta {
  lastEventId: string;
  lastEventName: string;
  retryMs?: number;
}
