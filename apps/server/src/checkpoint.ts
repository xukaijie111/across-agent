import { SqliteSaver } from "@langchain/langgraph-checkpoint-sqlite";

import { config } from "./config.js";

let checkpointer: SqliteSaver | null = null;

export function getCheckpointer(): SqliteSaver {
  if (!checkpointer) {
    checkpointer = SqliteSaver.fromConnString(config.dbPath);
  }
  return checkpointer;
}

import type { StreamCallbacks } from "./graph/streamCallbacks.js";

export function threadConfig(sessionId: string, callbacks?: StreamCallbacks) {
  return {
    configurable: {
      thread_id: sessionId,
      ...(callbacks?.onTextDelta ? { onTextDelta: callbacks.onTextDelta } : {}),
    },
  };
}
