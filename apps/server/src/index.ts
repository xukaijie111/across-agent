import cors from "cors";
import express from "express";
import type { Response } from "express";
import { z } from "zod";

import {
  extractBearerToken,
  issueAuthToken,
  resolveUsernameFromRequest,
  revokeAuthToken,
  verifyCredentials,
} from "./auth.js";
import { config } from "./config.js";
import {
  errorEvent,
  type ChatEvent,
} from "./graph/chatEvents.js";
import { defaultStreamRunner } from "./graph/streamRunner.js";
import { policyForAuth } from "./tools/policy.js";
import { sessionService } from "./session.js";
import "./tools/index.js";

const app = express();

app.use(
  cors({
    origin: "*",
    methods: ["GET", "POST", "OPTIONS"],
    allowedHeaders: ["Content-Type", "Authorization"],
  }),
);
app.use(express.json());

const chatBodySchema = z.object({
  session_id: z.string().min(1),
  message: z.string().min(1),
});

const approveBodySchema = z.object({
  session_id: z.string().min(1),
  interrupt_id: z.string().optional(),
  decisions: z
    .array(
      z.object({
        type: z.enum(["approve", "reject"]),
        message: z.string().optional(),
      }),
    )
    .min(1),
});

const loginBodySchema = z.object({
  username: z.string().min(1),
  password: z.string().min(1),
});

function writeSseFrame(res: Response, event: ChatEvent, eventId: number): void {
  res.write(`id: evt-${eventId}\n`);
  res.write("event: chat\n");
  res.write(`data: ${JSON.stringify(event)}\n\n`);
}

app.post("/auth/login", (req, res) => {
  const parsed = loginBodySchema.safeParse(req.body);
  if (!parsed.success) {
    res.status(400).json({ detail: "invalid request body" });
    return;
  }
  const { username, password } = parsed.data;
  if (!verifyCredentials(username, password)) {
    res.status(401).json({ detail: "invalid username or password" });
    return;
  }
  const token = issueAuthToken(username);
  res.json({
    token,
    username,
    policy: policyForAuth(username),
  });
});

app.post("/auth/logout", (req, res) => {
  const token = extractBearerToken(req.get("Authorization"));
  if (token) {
    revokeAuthToken(token);
  }
  res.json({ ok: true });
});

app.get("/auth/me", (req, res) => {
  const username = resolveUsernameFromRequest(req);
  if (!username) {
    res.status(401).json({ detail: "not authenticated" });
    return;
  }
  res.json({
    username,
    policy: policyForAuth(username),
  });
});

app.post("/chat/stream", async (req, res) => {
  const parsed = chatBodySchema.safeParse(req.body);
  if (!parsed.success) {
    res.status(400).json({ detail: "invalid request body" });
    return;
  }

  const { session_id: sessionId, message } = parsed.data;
  const userInput = message.trim();
  if (!userInput) {
    res.status(400).json({ detail: "message is empty" });
    return;
  }
  if (!sessionService.getSession(sessionId)) {
    res.status(404).json({ detail: "session not found" });
    return;
  }

  res.setHeader("Content-Type", "text/event-stream; charset=utf-8");
  res.setHeader("Cache-Control", "no-cache");
  res.setHeader("Connection", "keep-alive");

  let eventId = 0;
  const writeChatEvent = async (event: ChatEvent) => {
    eventId += 1;
    writeSseFrame(res, event, eventId);
  };

  try {
    await defaultStreamRunner.runTurn(sessionId, userInput, writeChatEvent);
  } catch (err) {
    const msg = err instanceof Error ? err.message : String(err);
    await writeChatEvent(errorEvent(`agent failed: ${msg}`));
  } finally {
    res.end();
  }
});

app.post("/chat/approve", async (req, res) => {
  const parsed = approveBodySchema.safeParse(req.body);
  if (!parsed.success) {
    res.status(400).json({ detail: "invalid request body" });
    return;
  }

  const { session_id: sessionId, interrupt_id: interruptId, decisions } = parsed.data;
  if (!sessionService.getSession(sessionId)) {
    res.status(404).json({ detail: "session not found" });
    return;
  }

  res.setHeader("Content-Type", "text/event-stream; charset=utf-8");
  res.setHeader("Cache-Control", "no-cache");
  res.setHeader("Connection", "keep-alive");

  let eventId = 0;
  const writeChatEvent = async (event: ChatEvent) => {
    eventId += 1;
    writeSseFrame(res, event, eventId);
  };

  try {
    await defaultStreamRunner.runApprove(sessionId, decisions, writeChatEvent, {
      interruptId,
    });
  } catch (err) {
    const msg = err instanceof Error ? err.message : String(err);
    await writeChatEvent(errorEvent(`approve failed: ${msg}`));
  } finally {
    res.end();
  }
});

app.post("/session/create", (req, res) => {
  const ownerUsername = resolveUsernameFromRequest(req);
  const { sessionId, policy } = sessionService.create({ ownerUsername });
  res.json({
    session_id: sessionId,
    policy,
    authenticated: Boolean(ownerUsername),
  });
});

app.post("/session/histroy", async (req, res) => {
  const sessionId = req.query.session_id;
  if (typeof sessionId !== "string" || !sessionId) {
    res.status(400).json({ detail: "session_id required" });
    return;
  }
  if (!sessionService.getSession(sessionId)) {
    res.status(404).json({ detail: "session not found" });
    return;
  }
  res.json(await defaultStreamRunner.getUiMessages(sessionId));
});

app.get("/ok", (_req, res) => {
  res.json({ ok: true });
});

app.listen(config.port, () => {
  console.log(`CrossAgent API (TS) http://127.0.0.1:${config.port}`);
});
