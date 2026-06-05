import type { RunnableConfig } from "@langchain/core/runnables";
import type OpenAI from "openai";

import {
  analyzeMessages,
  formatAnalysis,
  trimMessages,
  type ChatMessage,
} from "../context.js";
import { client, MODEL } from "../llm.js";
import { executeTool, getTools } from "../tools/index.js";
import type { AgentState } from "./state.js";
import { getStreamCallbacks } from "./streamCallbacks.js";

type ToolCallAccum = {
  id: string;
  type: "function";
  function: { name: string; arguments: string };
};

function toAssistantMessage(msg: OpenAI.Chat.Completions.ChatCompletionMessage): ChatMessage {
  const data: ChatMessage = {
    role: "assistant",
    content: msg.content ?? "",
  };
  if (msg.tool_calls?.length) {
    data.tool_calls = msg.tool_calls.map((call) => ({
      id: call.id,
      type: call.type,
      function: {
        name: call.function.name,
        arguments: call.function.arguments,
      },
    }));
  }
  return data;
}

function mergeToolCallDelta(
  acc: Map<number, ToolCallAccum>,
  deltas: OpenAI.Chat.Completions.ChatCompletionChunk.Choice.Delta.ToolCall[],
): void {
  for (const tc of deltas) {
    const index = tc.index ?? 0;
    let entry = acc.get(index);
    if (!entry) {
      entry = {
        id: tc.id ?? "",
        type: "function",
        function: { name: "", arguments: "" },
      };
      acc.set(index, entry);
    }
    if (tc.id) entry.id = tc.id;
    if (tc.function?.name) entry.function.name += tc.function.name;
    if (tc.function?.arguments) entry.function.arguments += tc.function.arguments;
  }
}

export async function callModel(
  state: AgentState,
  config?: RunnableConfig,
): Promise<Partial<AgentState>> {
  const messages = trimMessages(state.messages) as unknown as OpenAI.Chat.Completions.ChatCompletionMessageParam[];

  if (state.verbose) {
    console.log("[context]\n" + formatAnalysis(analyzeMessages(state.messages)));
  }

  const { onTextDelta } = getStreamCallbacks(
    config?.configurable as Record<string, unknown> | undefined,
  );

  const stream = await client.chat.completions.create({
    model: MODEL,
    messages,
    tools: getTools() as unknown as OpenAI.Chat.Completions.ChatCompletionTool[],
    tool_choice: "auto",
    stream: true,
  });

  let content = "";
  const toolAcc = new Map<number, ToolCallAccum>();

  for await (const chunk of stream) {
    const delta = chunk.choices[0]?.delta;
    if (!delta) continue;

    if (delta.content) {
      content += delta.content;
      onTextDelta?.(delta.content);
    }

    if (delta.tool_calls?.length) {
      mergeToolCallDelta(toolAcc, delta.tool_calls);
    }
  }

  const toolCalls = [...toolAcc.values()].filter((tc) => tc.id && tc.function.name);

  const assistantMsg: OpenAI.Chat.Completions.ChatCompletionMessage = {
    role: "assistant",
    content: content || null,
    refusal: null,
    ...(toolCalls.length
      ? {
          tool_calls: toolCalls.map((tc) => ({
            id: tc.id,
            type: "function" as const,
            function: {
              name: tc.function.name,
              arguments: tc.function.arguments,
            },
          })),
        }
      : {}),
  };

  return { messages: [toAssistantMessage(assistantMsg)] };
}

export async function executeTools(state: AgentState): Promise<Partial<AgentState>> {
  const last = state.messages[state.messages.length - 1];
  const toolCalls = (last?.tool_calls as Array<{
    id: string;
    function: { name: string; arguments: string };
  }>) ?? [];

  const toolMessages: ChatMessage[] = [];
  for (const toolCall of toolCalls) {
    let args: Record<string, unknown> = {};
    try {
      args = JSON.parse(toolCall.function.arguments || "{}") as Record<string, unknown>;
    } catch {
      args = {};
    }
    const result = await executeTool(toolCall.function.name, args);
    toolMessages.push({
      role: "tool",
      tool_call_id: toolCall.id,
      content: result,
    });
  }

  return { messages: toolMessages };
}

export function routeAfterAgent(state: AgentState): "tools" | "__end__" {
  const last = state.messages[state.messages.length - 1];
  const toolCalls = last?.tool_calls as unknown[] | undefined;
  if (toolCalls?.length) return "tools";
  return "__end__";
}
