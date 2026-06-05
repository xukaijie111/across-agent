import crypto from "node:crypto";

import {
  parseToolPolicy,
  policyForAuth,
  type ToolPolicy,
} from "./tools/policy.js";
import { getStorage } from "./storage/sqlite.js";

const PLACEHOLDER_NAME = "untitled";

export type CreateSessionResult = {
  sessionId: string;
  policy: ToolPolicy;
};

export class SessionService {
  create(options?: { name?: string | null; ownerUsername?: string | null }): CreateSessionResult {
    const sessionId = crypto.randomUUID().replace(/-/g, "");
    const ownerUsername = options?.ownerUsername ?? null;
    const policy = policyForAuth(ownerUsername);
    const finalName =
      options?.name && options.name.trim()
        ? options.name.trim()
        : `${PLACEHOLDER_NAME}-${sessionId.slice(0, 8)}`;
    getStorage().createSession(sessionId, finalName, policy, ownerUsername);
    return { sessionId, policy };
  }

  getSession(sessionId: string): Record<string, string> | null {
    return getStorage().getSessionById(sessionId);
  }

  getPolicy(sessionId: string): ToolPolicy {
    const row = getStorage().getSessionById(sessionId);
    if (!row) {
      return policyForAuth(null);
    }
    return parseToolPolicy(row.policy);
  }
}

export const sessionService = new SessionService();
