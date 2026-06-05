import { END, START, StateGraph } from "@langchain/langgraph";

import { getCheckpointer } from "../checkpoint.js";
import {
  approveTools,
  callModel,
  executeTools,
  routeAfterAgent,
  routeAfterApprove,
} from "./nodes.js";
import { AgentStateAnnotation } from "./state.js";

export function buildGraph(options?: { checkpointer?: boolean }) {
  const builder = new StateGraph(AgentStateAnnotation)
    .addNode("agent", callModel)
    .addNode("approve", approveTools)
    .addNode("tools", executeTools)
    .addEdge(START, "agent")
    .addConditionalEdges("agent", routeAfterAgent, {
      approve: "approve",
      __end__: END,
    })
    .addConditionalEdges("approve", routeAfterApprove, {
      tools: "tools",
      agent: "agent",
    })
    .addEdge("tools", "agent");

  if (options?.checkpointer === false) {
    return builder.compile();
  }
  return builder.compile({ checkpointer: getCheckpointer() });
}
