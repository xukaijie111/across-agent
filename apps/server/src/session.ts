import crypto from "node:crypto";

import { getStorage } from "./storage/sqlite.js";

const PLACEHOLDER_NAME = "untitled";

export class SessionService {
  create(name?: string | null): string {
    const sessionId = crypto.randomUUID().replace(/-/g, "");
    const finalName =
      name && name.trim() ? name.trim() : `${PLACEHOLDER_NAME}-${sessionId.slice(0, 8)}`;
    getStorage().createSession(sessionId, finalName);
    return sessionId;
  }

  getSession(sessionId: string): Record<string, string> | null {
    return getStorage().getSessionById(sessionId);
  }
}

export const sessionService = new SessionService();
