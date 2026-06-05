import { execFile } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { promisify } from "node:util";

import { registerTool } from "./registry.js";
import { relPath, resolvePath, toolError, toolOk, workspaceRoot } from "./workspace.js";

const execFileAsync = promisify(execFile);

async function runGit(args: string[], timeoutMs = 30_000): Promise<string> {
  const root = workspaceRoot();
  if (!fs.existsSync(path.join(root, ".git"))) {
    return toolError("当前工作区不是 git 仓库");
  }
  try {
    const { stdout, stderr } = await execFileAsync("git", args, {
      cwd: root,
      timeout: timeoutMs,
      maxBuffer: 10 * 1024 * 1024,
    });
    return toolOk({ output: stdout || stderr });
  } catch (err: unknown) {
    const e = err as { stderr?: string; stdout?: string; code?: number; message?: string };
    const detail =
      e.stderr?.trim() || e.stdout?.trim() || e.message || `git exit ${e.code ?? "?"}`;
    return toolError(detail);
  }
}

registerTool({
  name: "git_status",
  risk: "read",
  description: "查看工作区 git 状态（分支与变更摘要）。",
  parameters: { type: "object", properties: {} },
  handler: async () => runGit(["status", "--short", "--branch"]),
});

registerTool({
  name: "git_diff",
  risk: "read",
  description: "查看 git diff；path 可选，为相对工作区的文件或目录。",
  parameters: {
    type: "object",
    properties: { path: { type: "string" } },
  },
  handler: async (args) => {
    const gitArgs = ["diff"];
    const p = String(args.path ?? "").trim();
    if (p) {
      const resolved = resolvePath(p, true);
      gitArgs.push(relPath(resolved));
    }
    return runGit(gitArgs);
  },
});

registerTool({
  name: "git_log",
  risk: "read",
  description: "查看最近 git 提交记录。",
  parameters: {
    type: "object",
    properties: { max_count: { type: "integer" } },
  },
  handler: async (args) => {
    const count = Math.max(1, Math.min(Number(args.max_count ?? 10), 50));
    return runGit(["log", `-${count}`, "--oneline", "--decorate"]);
  },
});
