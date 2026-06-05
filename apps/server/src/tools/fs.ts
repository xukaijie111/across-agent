import fs from "node:fs/promises";
import path from "node:path";

import { registerTool } from "./registry.js";
import {
  readTextLimited,
  relPath,
  resolvePath,
  toolError,
  toolOk,
  workspaceRoot,
} from "./workspace.js";

const MAX_LIST_ENTRIES = 500;
const MAX_GLOB_MATCHES = 200;
const MAX_GREP_MATCHES = 100;
const MAX_GREP_FILE_BYTES = 500_000;

async function walkFiles(base: string, pattern: string): Promise<string[]> {
  const glob = pattern.includes("*") ? pattern : `**/${pattern}`;
  const results: string[] = [];

  async function walk(dir: string): Promise<void> {
    const entries = await fs.readdir(dir, { withFileTypes: true });
    for (const entry of entries) {
      const full = path.join(dir, entry.name);
      if (entry.isDirectory()) {
        await walk(full);
      } else if (entry.isFile()) {
        results.push(full);
      }
    }
  }

  await walk(base);

  const minimatch = (file: string, pat: string): boolean => {
    const rel = path.relative(base, file).replace(/\\/g, "/");
    const re = new RegExp(
      "^" +
        pat
          .replace(/\*\*/g, "§§")
          .replace(/\*/g, "[^/]*")
          .replace(/§§/g, ".*")
          .replace(/\./g, "\\.") +
        "$",
    );
    return re.test(rel) || rel.endsWith(pat.replace(/\*/g, ""));
  };

  return results.filter((f) => minimatch(f, glob)).slice(0, MAX_GLOB_MATCHES + 1);
}

registerTool({
  name: "read_file",
  description: "读取工作区内的文本文件。path 为相对工作区的路径。",
  parameters: {
    type: "object",
    properties: { path: { type: "string" } },
    required: ["path"],
  },
  handler: async (args) => {
    try {
      const resolved = resolvePath(String(args.path), true);
      const stat = await fs.stat(resolved);
      if (!stat.isFile()) return toolError(`不是文件: ${resolved}`);
      const content = await readTextLimited(resolved);
      return toolOk({ path: relPath(resolved), content });
    } catch (err) {
      return toolError(err instanceof Error ? err.message : String(err));
    }
  },
});

registerTool({
  name: "list_dir",
  description: "列出工作区目录下的文件和子目录。path 默认为工作区根目录。",
  parameters: {
    type: "object",
    properties: { path: { type: "string" } },
  },
  handler: async (args) => {
    try {
      const resolved = resolvePath(String(args.path ?? "."), true);
      const stat = await fs.stat(resolved);
      if (!stat.isDirectory()) return toolError(`不是目录: ${resolved}`);
      const entries = await fs.readdir(resolved, { withFileTypes: true });
      entries.sort((a, b) => {
        if (a.isDirectory() !== b.isDirectory()) return a.isDirectory() ? -1 : 1;
        return a.name.localeCompare(b.name);
      });
      const truncated = entries.length > MAX_LIST_ENTRIES;
      const slice = truncated ? entries.slice(0, MAX_LIST_ENTRIES) : entries;
      const items = await Promise.all(
        slice.map(async (e) => ({
          name: e.name,
          type: e.isDirectory() ? "dir" : "file",
          path: relPath(path.join(resolved, e.name)),
        })),
      );
      return toolOk({
        path: relPath(resolved),
        entries: items,
        truncated,
        total: items.length,
      });
    } catch (err) {
      return toolError(err instanceof Error ? err.message : String(err));
    }
  },
});

registerTool({
  name: "search_files",
  description: "按 glob 模式搜索文件，例如 **/*.json 或 src/**/*.tsx。",
  parameters: {
    type: "object",
    properties: {
      pattern: { type: "string" },
      path: { type: "string" },
    },
    required: ["pattern"],
  },
  handler: async (args) => {
    try {
      const base = resolvePath(String(args.path ?? "."), true);
      const stat = await fs.stat(base);
      if (!stat.isDirectory()) return toolError(`不是目录: ${base}`);
      const pattern = String(args.pattern);
      const all = await walkFiles(base, pattern);
      const truncated = all.length > MAX_GLOB_MATCHES;
      const matches = all.slice(0, MAX_GLOB_MATCHES).map(relPath);
      return toolOk({
        pattern,
        path: relPath(base),
        matches,
        truncated,
        total: all.length,
      });
    } catch (err) {
      return toolError(err instanceof Error ? err.message : String(err));
    }
  },
});

registerTool({
  name: "grep_files",
  description: "在文件内容中搜索正则 pattern，返回匹配行。glob 限定文件范围，默认 **/*。",
  parameters: {
    type: "object",
    properties: {
      pattern: { type: "string" },
      path: { type: "string" },
      glob: { type: "string" },
    },
    required: ["pattern"],
  },
  handler: async (args) => {
    try {
      const base = resolvePath(String(args.path ?? "."), true);
      const globPat = String(args.glob ?? "**/*");
      const regex = new RegExp(String(args.pattern));
      const files = await walkFiles(base, globPat);
      const hits: Array<{ path: string; line: number; text: string }> = [];
      for (const file of files) {
        const st = await fs.stat(file);
        if (st.size > MAX_GREP_FILE_BYTES) continue;
        const text = await fs.readFile(file, "utf8");
        for (const [i, line] of text.split("\n").entries()) {
          if (regex.test(line)) {
            hits.push({ path: relPath(file), line: i + 1, text: line.slice(0, 300) });
            if (hits.length >= MAX_GREP_MATCHES) {
              return toolOk({
                pattern: String(args.pattern),
                path: relPath(base),
                matches: hits,
                truncated: true,
              });
            }
          }
        }
      }
      return toolOk({
        pattern: String(args.pattern),
        path: relPath(base),
        matches: hits,
        truncated: false,
      });
    } catch (err) {
      return toolError(err instanceof Error ? err.message : String(err));
    }
  },
});

registerTool({
  name: "write_file",
  description: "写入工作区内的文本文件。仅在用户明确要求修改时使用。",
  parameters: {
    type: "object",
    properties: {
      path: { type: "string" },
      content: { type: "string" },
    },
    required: ["path", "content"],
  },
  handler: async (args) => {
    try {
      const resolved = resolvePath(String(args.path));
      await fs.mkdir(path.dirname(resolved), { recursive: true });
      const content = String(args.content);
      await fs.writeFile(resolved, content, "utf8");
      return toolOk({
        path: relPath(resolved),
        bytes: Buffer.byteLength(content, "utf8"),
      });
    } catch (err) {
      return toolError(err instanceof Error ? err.message : String(err));
    }
  },
});

// side-effect: ensure workspace root exists
void workspaceRoot();
