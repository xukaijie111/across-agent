import { END, START, StateGraph } from "@langchain/langgraph";

import { getCheckpointer } from "../checkpoint.js";
import { callModel, executeTools, routeAfterAgent } from "./nodes.js";
import { AgentStateAnnotation } from "./state.js";

export function buildGraph(options?: { checkpointer?: boolean }) {
  const builder = new StateGraph(AgentStateAnnotation)
    .addNode("agent", callModel)
    .addNode("tools", executeTools)
    .addEdge(START, "agent")
    .addConditionalEdges("agent", routeAfterAgent, {
      tools: "tools",
      __end__: END,
    })
    .addEdge("tools", "agent");

  if (options?.checkpointer === false) {
    return builder.compile();
  }
  return builder.compile({ checkpointer: getCheckpointer() });
}
