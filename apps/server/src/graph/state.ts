import { Annotation } from "@langchain/langgraph";

import type { ChatMessage } from "../context.js";

export const AgentStateAnnotation = Annotation.Root({
  messages: Annotation<ChatMessage[]>({
    reducer: (left, right) => left.concat(right),
    default: () => [],
  }),
  verbose: Annotation<boolean>({
    reducer: (_left, right) => right,
    default: () => false,
  }),
  /** approve 节点写入；tools 节点只执行列表内的 tool_call_id */
  approvedToolCallIds: Annotation<string[]>({
    reducer: (_left, right) => right,
    default: () => [],
  }),
});

export type AgentState = typeof AgentStateAnnotation.State;
