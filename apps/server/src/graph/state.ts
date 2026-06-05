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
});

export type AgentState = typeof AgentStateAnnotation.State;
