export interface AgentInfo {
  id: string;
  name: string;
  description: string;
  enabled: boolean;
}

export interface InterruptPayload {
  type: string;
  prompt: string;
  options?: string[];
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  streaming?: boolean;
  interrupt?: InterruptPayload;
  awaitingAction?: boolean;
}

export interface SessionSummary {
  session_id: string;
  agent_id: string;
  title: string;
  updated_at?: string | null;
}

export interface SessionDetail {
  session_id: string;
  agent_id: string;
  title: string;
  state: {
    awaiting_resume: boolean;
    interrupt?: InterruptPayload;
  };
}

export interface HistoryMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  interrupt?: InterruptPayload;
  awaiting_action?: boolean;
}

export type SseHandler = (event: string, data: Record<string, unknown>) => void;
