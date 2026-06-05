import { threadConfig } from "../checkpoint.js";
import { trimMessages, type ChatMessage } from "../context.js";
import {
  doneEvent,
  textEvent,
  toolEndEvent,
  toolStartEvent,
  type ChatEvent,
  type ContentFormat,
} from "./chatEvents.js";
import { buildGraph } from "./graph.js";
import { SYSTEM_PROMPT } from "./systemPrompt.js";
import type { AgentState } from "./state.js";

export type ChatEventHandler = (event: ChatEvent) => void | Promise<void>;

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

export class StreamRunner {
  private graph = buildGraph();

  async getUiMessages(sessionId: string): Promise<
    Array<{
      role: string;
      content: string;
      format: ContentFormat;
    }>
  > {
    const snapshot = await this.graph.getState(threadConfig(sessionId));
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

  /**
   * 跑一轮对话，每产生一个 ChatEvent 调用 onEvent（无 generator / yield）。
   */
  async runTurn(
    sessionId: string,
    userInput: string,
    onEvent: ChatEventHandler,
    options?: { verbose?: boolean },
  ): Promise<void> {
    const config = threadConfig(sessionId);
    const snapshot = await this.graph.getState(config);
    const existing = (snapshot.values as AgentState | undefined)?.messages ?? [];

    const inputMessages = trimMessages(buildInputMessages(userInput, existing));
    const state: AgentState = {
      messages: inputMessages,
      verbose: options?.verbose ?? false,
    };

    let streamedTextForCurrentAgent = false;
    const { schedule, flush } = createEmitScheduler(onEvent);

    const runConfig = threadConfig(sessionId, {
      onTextDelta: (delta) => {
        streamedTextForCurrentAgent = true;
        void schedule(textEvent(delta));
      },
    });

    const graphStream = await this.graph.stream(state, {
      ...runConfig,
      streamMode: "updates",
    });

    for await (const update of graphStream) {
      await flush();

      if ("agent" in update) {
        const msgs = (update.agent as Partial<AgentState>).messages ?? [];
        if (!msgs.length) continue;
        const last = msgs[msgs.length - 1];

        if ((last.tool_calls as unknown[])?.length) {
          for (const tc of last.tool_calls as Array<{
            id: string;
            function: { name: string; arguments: string };
          }>) {
            await schedule(
              toolStartEvent(
                tc.id ?? "",
                tc.function?.name ?? "",
                parseToolArgs(tc.function?.arguments ?? "{}"),
              ),
            );
          }
        } else {
          const content = String(last.content ?? "");
          if (content && !streamedTextForCurrentAgent) {
            await schedule(textEvent(content));
          }
        }
        streamedTextForCurrentAgent = false;
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
    await schedule(doneEvent());
  }
}

export const defaultStreamRunner = new StreamRunner();
