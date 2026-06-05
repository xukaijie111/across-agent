import path from "node:path";
import fs from "node:fs";

import { config } from "../config.js";

const MAX_READ_BYTES = 200_000;

export function workspaceRoot(): string {
  return config.workspaceRoot;
}

export function resolvePath(inputPath: string, mustExist = false): string {
  const root = workspaceRoot();
  const raw = (inputPath || ".").trim();
  const candidate = path.isAbsolute(raw) ? raw : path.join(root, raw);
  const resolved = path.resolve(candidate);
  const rootResolved = path.resolve(root);
  const relative = path.relative(rootResolved, resolved);
  if (relative.startsWith("..") || path.isAbsolute(relative)) {
    throw new Error(`路径超出工作区 ${rootResolved}: ${inputPath}`);
  }
  if (mustExist && !fs.existsSync(resolved)) {
    throw new Error(`路径不存在: ${resolved}`);
  }
  return resolved;
}

export function relPath(absPath: string): string {
  return path.relative(workspaceRoot(), absPath);
}

export function toolError(message: string, extra: Record<string, unknown> = {}): string {
  return JSON.stringify({ ok: false, error: message, ...extra });
}

export function toolOk(payload: Record<string, unknown>): string {
  return JSON.stringify({ ok: true, ...payload });
}

export async function readTextLimited(
  filePath: string,
  maxBytes = MAX_READ_BYTES,
): Promise<string> {
  const { stat, readFile } = await import("node:fs/promises");
  const size = (await stat(filePath)).size;
  if (size > maxBytes) {
    throw new Error(`文件过大 (${size} bytes)，上限 ${maxBytes}`);
  }
  return readFile(filePath, "utf8");
}
