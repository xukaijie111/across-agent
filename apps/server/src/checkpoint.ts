import { SqliteSaver } from "@langchain/langgraph-checkpoint-sqlite";

import { config } from "./config.js";

let checkpointer: SqliteSaver | null = null;

export function getCheckpointer(): SqliteSaver {
  if (!checkpointer) {
    checkpointer = SqliteSaver.fromConnString(config.checkpointDbPath);
  }
  return checkpointer;
}

import type { StreamCallbacks } from "./graph/streamCallbacks.js";
import type { ToolPolicy } from "./tools/policy.js";

export type ThreadConfigOptions = {
  callbacks?: StreamCallbacks;
  toolPolicy?: ToolPolicy;
};

export function threadConfig(sessionId: string, options?: ThreadConfigOptions) {
  return {
    configurable: {
      thread_id: sessionId,
      ...(options?.toolPolicy ? { toolPolicy: options.toolPolicy } : {}),
      ...(options?.callbacks?.onTextDelta
        ? { onTextDelta: options.callbacks.onTextDelta }
        : {}),
      ...(options?.callbacks?.onToolStart
        ? { onToolStart: options.callbacks.onToolStart }
        : {}),
    },
  };
}
