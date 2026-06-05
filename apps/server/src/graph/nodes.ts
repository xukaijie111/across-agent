import type { RunnableConfig } from "@langchain/core/runnables";
import { interrupt } from "@langchain/langgraph";
import type OpenAI from "openai";

import {
  analyzeMessages,
  formatAnalysis,
  trimMessages,
  type ChatMessage,
} from "../context.js";
import { client, MODEL } from "../llm.js";
import { executeTool, getToolRisk, getTools } from "../tools/index.js";
import { isToolAllowed, requiresHitlApproval } from "../tools/policy.js";
import { parseHitlResume, type HitlRequest } from "./hitl.js";
import type { AgentState } from "./state.js";
import { getStreamCallbacks, getToolPolicy } from "./streamCallbacks.js";

type ToolCall = {
  id: string;
  type: "function";
  function: { name: string; arguments: string };
};

type ToolCallAccum = ToolCall;

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

function parseToolArgs(raw: string): Record<string, unknown> {
  try {
    const parsed = JSON.parse(raw || "{}") as unknown;
    return typeof parsed === "object" && parsed !== null
      ? (parsed as Record<string, unknown>)
      : {};
  } catch {
    return {};
  }
}

function lastAssistantToolCalls(state: AgentState): ToolCall[] {
  const last = state.messages[state.messages.length - 1];
  return (last?.tool_calls as ToolCall[] | undefined) ?? [];
}

export async function callModel(
  state: AgentState,
  config?: RunnableConfig,
): Promise<Partial<AgentState>> {
  const messages = trimMessages(state.messages) as unknown as OpenAI.Chat.Completions.ChatCompletionMessageParam[];

  if (state.verbose) {
    console.log("[context]\n" + formatAnalysis(analyzeMessages(state.messages)));
  }

  const configurable = config?.configurable as Record<string, unknown> | undefined;
  const { onTextDelta } = getStreamCallbacks(configurable);
  const toolPolicy = getToolPolicy(configurable);

  const stream = await client.chat.completions.create({
    model: MODEL,
    messages,
    tools: getTools(toolPolicy) as unknown as OpenAI.Chat.Completions.ChatCompletionTool[],
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

  return {
    messages: [toAssistantMessage(assistantMsg)],
    approvedToolCallIds: [],
  };
}

export async function approveTools(
  state: AgentState,
  config?: RunnableConfig,
): Promise<Partial<AgentState>> {
  const toolPolicy = getToolPolicy(config?.configurable as Record<string, unknown> | undefined);
  const toolCalls = lastAssistantToolCalls(state);

  const autoApproved: string[] = [];
  const needsHitl: ToolCall[] = [];

  for (const tc of toolCalls) {
    const risk = getToolRisk(tc.function.name);
    if (risk && requiresHitlApproval(risk) && isToolAllowed(risk, toolPolicy)) {
      needsHitl.push(tc);
    } else {
      autoApproved.push(tc.id);
    }
  }

  const approvedIds = [...autoApproved];
  const rejectMessages: ChatMessage[] = [];

  if (needsHitl.length > 0) {
    const hitlRequest: HitlRequest = {
      action_requests: needsHitl.map((tc) => ({
        name: tc.function.name,
        args: parseToolArgs(tc.function.arguments),
      })),
    };

    const resumeValue = interrupt(hitlRequest);
    const decisions = parseHitlResume(resumeValue);

    for (let i = 0; i < needsHitl.length; i++) {
      const tc = needsHitl[i];
      const decision = decisions[i];
      if (decision?.type === "approve") {
        approvedIds.push(tc.id);
        continue;
      }
      const message =
        decision?.type === "reject" && decision.message
          ? decision.message
          : "User rejected tool execution";
      rejectMessages.push({
        role: "tool",
        tool_call_id: tc.id,
        content: JSON.stringify({ ok: false, error: message }),
      });
    }
  }

  const patch: Partial<AgentState> = {
    approvedToolCallIds: approvedIds,
  };
  if (rejectMessages.length > 0) {
    patch.messages = rejectMessages;
  }
  return patch;
}

export async function executeTools(
  state: AgentState,
  config?: RunnableConfig,
): Promise<Partial<AgentState>> {
  const configurable = config?.configurable as Record<string, unknown> | undefined;
  const { onToolStart } = getStreamCallbacks(configurable);
  const toolPolicy = getToolPolicy(configurable);
  const toolCalls = lastAssistantToolCalls(state);
  const approved = new Set(state.approvedToolCallIds ?? []);

  const toolMessages: ChatMessage[] = [];
  for (const toolCall of toolCalls) {
    if (!approved.has(toolCall.id)) {
      continue;
    }
    const args = parseToolArgs(toolCall.function.arguments);
    const result = await executeTool(
      toolCall.function.name,
      args,
      toolPolicy,
      {
        toolCallId: toolCall.id,
        onStart: onToolStart,
      },
    );
    toolMessages.push({
      role: "tool",
      tool_call_id: toolCall.id,
      content: result,
    });
  }

  return {
    messages: toolMessages,
    approvedToolCallIds: [],
  };
}

export function routeAfterAgent(state: AgentState): "approve" | "__end__" {
  const toolCalls = lastAssistantToolCalls(state);
  if (toolCalls.length > 0) return "approve";
  return "__end__";
}

export function routeAfterApprove(state: AgentState): "tools" | "agent" {
  const approved = state.approvedToolCallIds ?? [];
  return approved.length > 0 ? "tools" : "agent";
}
