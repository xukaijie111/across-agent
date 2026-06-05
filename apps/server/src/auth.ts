import crypto from "node:crypto";
import type { Request } from "express";

import { config } from "./config.js";
import { getStorage } from "./storage/sqlite.js";

const TOKEN_TTL_MS = 7 * 24 * 60 * 60 * 1000;

export function verifyCredentials(username: string, password: string): boolean {
  return username === config.authUsername && password === config.authPassword;
}

export function issueAuthToken(username: string): string {
  const token = crypto.randomUUID().replace(/-/g, "");
  const expiresAt = new Date(Date.now() + TOKEN_TTL_MS).toISOString();
  getStorage().createAuthToken(token, username, expiresAt);
  return token;
}

export function revokeAuthToken(token: string): void {
  getStorage().deleteAuthToken(token);
}

export function resolveUsernameFromAuthorization(
  authorization: string | undefined,
): string | null {
  if (!authorization?.startsWith("Bearer ")) {
    return null;
  }
  const token = authorization.slice("Bearer ".length).trim();
  if (!token) {
    return null;
  }
  return getStorage().getUsernameByToken(token);
}

export function resolveUsernameFromRequest(req: Request): string | null {
  return resolveUsernameFromAuthorization(req.get("Authorization"));
}

export function extractBearerToken(authorization: string | undefined): string | null {
  if (!authorization?.startsWith("Bearer ")) {
    return null;
  }
  const token = authorization.slice("Bearer ".length).trim();
  return token || null;
}
