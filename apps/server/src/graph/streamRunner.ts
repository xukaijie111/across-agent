import { Command } from "@langchain/langgraph";

import { threadConfig } from "../checkpoint.js";
import { sessionService } from "../session.js";
import { trimMessages, type ChatMessage } from "../context.js";
import {
  approvalPendingEvent,
  doneEvent,
  textEvent,
  toolConfirmEvent,
  toolEndEvent,
  toolStartEvent,
  type ChatEvent,
  type ContentFormat,
} from "./chatEvents.js";
import { buildGraph } from "./graph.js";
import type { HitlDecision, HitlRequest } from "./hitl.js";
import { SYSTEM_PROMPT } from "./systemPrompt.js";
import type { AgentState } from "./state.js";

export type ChatEventHandler = (event: ChatEvent) => void | Promise<void>;

export type RunTurnResult = {
  interrupted: boolean;
};

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

function toolPayload(content: string): { result: string | null; error: string | null } {
  try {
    const data = JSON.parse(content) as { ok?: boolean };
    if (typeof data === "object" && data?.ok === false) {
      return { result: null, error: content };
    }
    return { result: content, error: null };
  } catch {
    return { result: content, error: null };
  }
}

function buildInputMessages(userInput: string, existing: ChatMessage[]): ChatMessage[] {
  if (!existing.length) {
    return [
      { role: "system", content: SYSTEM_PROMPT },
      { role: "user", content: userInput },
    ];
  }
  return [{ role: "user", content: userInput }];
}

async function emit(handler: ChatEventHandler, event: ChatEvent): Promise<void> {
  await handler(event);
}

/** 串行发送 SSE，避免 onTextDelta 与 updates 事件并发导致前端乱序 */
function createEmitScheduler(handler: ChatEventHandler) {
  let tail = Promise.resolve();

  const schedule = (event: ChatEvent): Promise<void> => {
    const run = tail.then(() => emit(handler, event));
    tail = run.then(
      () => undefined,
      () => undefined,
    );
    return run;
  };

  const flush = (): Promise<void> => tail;

  return { schedule, flush };
}

type GraphUpdate = Record<string, unknown>;

type InterruptRecord = {
  id?: string;
  value?: unknown;
};

function isHitlRequest(value: unknown): value is HitlRequest {
  return (
    typeof value === "object" &&
    value !== null &&
    Array.isArray((value as HitlRequest).action_requests)
  );
}

export class StreamRunner {
  private graph = buildGraph();

  async getUiMessages(sessionId: string): Promise<
    Array<{
      role: string;
      content: string;
      format: ContentFormat;
    }>
  > {
    let snapshot;
    try {
      snapshot = await this.graph.getState(threadConfig(sessionId));
    } catch (err) {
      console.warn(
        `[checkpoint] getState failed for ${sessionId}:`,
        err instanceof Error ? err.message : err,
      );
      return [];
    }
    const raw = (snapshot.values as AgentState | undefined)?.messages ?? [];
    const out: Array<{ role: string; content: string; format: ContentFormat }> = [];
    for (const msg of raw) {
      if (msg.role === "user") {
        out.push({
          role: "user",
          content: String(msg.content ?? ""),
          format: "plain",
        });
      } else if (msg.role === "assistant" && !(msg.tool_calls as unknown[])?.length) {
        const content = String(msg.content ?? "");
        if (content) {
          out.push({ role: "assistant", content, format: "markdown" });
        }
      }
    }
    return out;
  }

  private async consumeGraphStream(
    graphStream: AsyncIterable<GraphUpdate>,
    onEvent: ChatEventHandler,
    options?: {
      emitDone?: boolean;
      streamedTextForCurrentAgentRef?: () => boolean;
      resetStreamedText?: () => void;
      scheduler?: ReturnType<typeof createEmitScheduler>;
    },
  ): Promise<RunTurnResult> {
    let interrupted = false;
    const scheduler = options?.scheduler ?? createEmitScheduler(onEvent);
    const { schedule, flush } = scheduler;
    const streamedTextRef = options?.streamedTextForCurrentAgentRef ?? (() => false);
    const resetStreamedText = options?.resetStreamedText ?? (() => undefined);

    for await (const update of graphStream) {
      await flush();

      if ("__interrupt__" in update) {
        interrupted = true;
        const records = update.__interrupt__ as InterruptRecord[];
        for (const record of records) {
          const value = record.value;
          if (!isHitlRequest(value)) continue;
          await schedule(
            toolConfirmEvent(record.id ?? "", value.action_requests),
          );
        }
        await schedule(approvalPendingEvent());
        continue;
      }

      if ("agent" in update) {
        const msgs = (update.agent as Partial<AgentState>).messages ?? [];
        if (!msgs.length) continue;
        const last = msgs[msgs.length - 1];

        if (!(last.tool_calls as unknown[])?.length) {
          const content = String(last.content ?? "");
          if (content && !streamedTextRef()) {
            await schedule(textEvent(content));
          }
        }
        resetStreamedText();
      }

      if ("approve" in update) {
        const toolMsgs = (update.approve as Partial<AgentState>).messages ?? [];
        for (const toolMsg of toolMsgs) {
          const content = String(toolMsg.content ?? "");
          const { result, error } = toolPayload(content);
          await schedule(
            toolEndEvent(String(toolMsg.tool_call_id ?? ""), result, error),
          );
        }
      }

      if ("tools" in update) {
        const toolMsgs = (update.tools as Partial<AgentState>).messages ?? [];
        for (const toolMsg of toolMsgs) {
          const content = String(toolMsg.content ?? "");
          const { result, error } = toolPayload(content);
          await schedule(
            toolEndEvent(String(toolMsg.tool_call_id ?? ""), result, error),
          );
        }
      }
    }

    await flush();
    if (!interrupted && options?.emitDone !== false) {
      await schedule(doneEvent());
    }
    return { interrupted };
  }

  /**
   * 跑一轮对话，每产生一个 ChatEvent 调用 onEvent（无 generator / yield）。
   */
  async runTurn(
    sessionId: string,
    userInput: string,
    onEvent: ChatEventHandler,
    options?: { verbose?: boolean },
  ): Promise<RunTurnResult> {
    const toolPolicy = sessionService.getPolicy(sessionId);
    const config = threadConfig(sessionId, { toolPolicy });
    const snapshot = await this.graph.getState(config);
    const existing = (snapshot.values as AgentState | undefined)?.messages ?? [];

    const inputMessages = trimMessages(buildInputMessages(userInput, existing));
    const state: AgentState = {
      messages: inputMessages,
      verbose: options?.verbose ?? false,
      approvedToolCallIds: [],
    };

    let streamedTextForCurrentAgent = false;
    const scheduler = createEmitScheduler(onEvent);

    const runConfig = threadConfig(sessionId, {
      toolPolicy,
      callbacks: {
        onTextDelta: (delta) => {
          streamedTextForCurrentAgent = true;
          void scheduler.schedule(textEvent(delta));
        },
        onToolStart: (id, name, args) => {
          void scheduler.schedule(toolStartEvent(id, name, args));
        },
      },
    });

    const graphStream = await this.graph.stream(state, {
      ...runConfig,
      streamMode: "updates",
    });

    return this.consumeGraphStream(graphStream, onEvent, {
      streamedTextForCurrentAgentRef: () => streamedTextForCurrentAgent,
      resetStreamedText: () => {
        streamedTextForCurrentAgent = false;
      },
      scheduler,
    });
  }

  /**
   * 用户确认后 resume 挂起的图，继续 SSE 推送直至结束或再次 interrupt。
   */
  async runApprove(
    sessionId: string,
    decisions: HitlDecision[],
    onEvent: ChatEventHandler,
    options?: { interruptId?: string },
  ): Promise<RunTurnResult> {
    const toolPolicy = sessionService.getPolicy(sessionId);
    const scheduler = createEmitScheduler(onEvent);
    const runConfig = threadConfig(sessionId, {
      toolPolicy,
      callbacks: {
        onToolStart: (id, name, args) => {
          void scheduler.schedule(toolStartEvent(id, name, args));
        },
      },
    });

    const resumeBody = options?.interruptId
      ? { [options.interruptId]: { decisions } }
      : { decisions };

    const graphStream = await this.graph.stream(new Command({ resume: resumeBody }), {
      ...runConfig,
      streamMode: "updates",
    });

    return this.consumeGraphStream(graphStream, onEvent, { scheduler });
  }
}

export const defaultStreamRunner = new StreamRunner();
