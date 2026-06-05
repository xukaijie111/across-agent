import type { ChatEvent } from "@/types/chat";

const sleep = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

let eventSeq = 0;

/** 完整 SSE 帧：retry / id / event / data（多行 data 用 \n 拼接） */
function encodeSseFrame(
  data: ChatEvent,
  options?: { event?: string; withRetry?: number },
): Uint8Array {
  eventSeq += 1;
  const lines: string[] = [];

  if (options?.withRetry !== undefined) {
    lines.push(`retry: ${options.withRetry}`);
  }
  lines.push(`id: evt-${eventSeq}`);
  lines.push(`event: ${options?.event ?? "chat"}`);
  lines.push(`data: ${JSON.stringify(data)}`);
  lines.push("", "");

  return new TextEncoder().encode(lines.join("\n"));
}

async function streamText(
  controller: ReadableStreamDefaultController<Uint8Array>,
  text: string,
  delayMs = 30,
) {
  for (const char of text) {
    controller.enqueue(encodeSseFrame({ type: "text", delta: char, format: "markdown" }));
    await sleep(delayMs);
  }
}

async function runMockReply(
  controller: ReadableStreamDefaultController<Uint8Array>,
  userMessage: string,
) {
  controller.enqueue(new TextEncoder().encode("retry: 3000\n\n"));

  const wantsTool =
    /工具|tool|read_file|读文件/i.test(userMessage) ||
    userMessage.includes("package.json");

  if (wantsTool) {
    await streamText(controller, "好，我先调 read_file 看一下。\n\n", 20);
    await sleep(400);

    controller.enqueue(
      encodeSseFrame({
        type: "tool_start",
        id: "call_mock_1",
        name: "read_file",
        args: { path: "package.json" },
      }),
    );
    await sleep(900);

    controller.enqueue(
      encodeSseFrame({
        type: "tool_end",
        id: "call_mock_1",
        result: JSON.stringify(
          { name: "web", version: "0.1.0", private: true },
          null,
          2,
        ),
      }),
    );
    await sleep(300);

    await streamText(
      controller,
      "读到了：这是个 Next.js 前端项目，mock 流式 + Tool 卡片都能测。",
    );
    return;
  }

  if (/构建|build|终端/i.test(userMessage)) {
    await streamText(
      controller,
      "构建 mock：detect_framework → uni-app\nrun_build → success\n（Day4 会接 xterm 终端）",
      15,
    );
    return;
  }

  await streamText(
    controller,
    `收到：「${userMessage}」\n\n这是 mock 回复。试试发「读文件」或「tool」看 Tool 卡片；Backend 接好后换成真 Agent。`,
    20,
  );
}

export async function POST(request: Request) {
  const body = (await request.json()) as { message?: string };
  const userMessage = body.message?.trim() ?? "你好";

  eventSeq = 0;

  const stream = new ReadableStream<Uint8Array>({
    async start(controller) {
      try {
        await runMockReply(controller, userMessage);
        controller.enqueue(encodeSseFrame({ type: "done" }));
      } catch {
        controller.enqueue(
          encodeSseFrame({ type: "error", message: "mock stream failed" }),
        );
      } finally {
        controller.close();
      }
    },
  });

  return new Response(stream, {
    headers: {
      "Content-Type": "text/event-stream; charset=utf-8",
      "Cache-Control": "no-cache, no-transform",
      Connection: "keep-alive",
    },
  });
}
