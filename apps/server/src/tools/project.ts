import { execFile } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { promisify } from "node:util";

import { registerTool } from "./registry.js";
import { toolError, toolOk, workspaceRoot } from "./workspace.js";

const execFileAsync = promisify(execFile);

const BUILD_TIMEOUT_SEC = 600;
const BUILD_OUTPUT_TAIL = 4000;

const TARGET_SCRIPTS: Record<string, string[]> = {
  weixin: ["build:weapp", "build:mp-weixin", "build:weixin", "dev:mp-weixin"],
  alipay: ["build:alipay", "build:mp-alipay", "dev:mp-alipay"],
  h5: ["build:h5", "build:web", "build"],
  tt: ["build:tt", "build:mp-toutiao"],
  baidu: ["build:swan", "build:mp-baidu"],
};

function readPackageJson(root: string): Record<string, unknown> | null {
  const pkg = path.join(root, "package.json");
  if (!fs.existsSync(pkg)) return null;
  try {
    const data = JSON.parse(fs.readFileSync(pkg, "utf8"));
    return typeof data === "object" && data ? (data as Record<string, unknown>) : null;
  } catch {
    return null;
  }
}

function collectDeps(pkg: Record<string, unknown>): Record<string, string> {
  const deps: Record<string, string> = {};
  for (const key of ["dependencies", "devDependencies", "peerDependencies"]) {
    const raw = pkg[key];
    if (raw && typeof raw === "object") {
      Object.assign(deps, raw as Record<string, string>);
    }
  }
  return deps;
}

function detectSignals(root: string, deps: Record<string, string>): string[] {
  const signals: string[] = [];
  if (Object.keys(deps).some((k) => k.startsWith("@tarojs/"))) signals.push("taro");
  if (Object.keys(deps).some((k) => k.startsWith("@dcloudio/") || k.includes("uni-app"))) {
    signals.push("uni-app");
  }
  if (fs.existsSync(path.join(root, "pages.json")) || fs.existsSync(path.join(root, "manifest.json"))) {
    if (!signals.includes("uni-app")) signals.push("uni-app-like");
  }
  if (Object.keys(deps).some((k) => k.toLowerCase().includes("morjs")) || fs.existsSync(path.join(root, "mor.config.js"))) {
    signals.push("morjs");
  }
  if (fs.existsSync(path.join(root, "project.config.json"))) {
    signals.push("wechat-miniprogram-config");
  }
  return signals;
}

function packageManager(root: string): string {
  if (fs.existsSync(path.join(root, "pnpm-lock.yaml"))) return "pnpm";
  if (fs.existsSync(path.join(root, "yarn.lock"))) return "yarn";
  return "npm";
}

function pickBuildScript(scripts: Record<string, string>, target: string): string | null {
  for (const name of [...(TARGET_SCRIPTS[target] ?? []), "build"]) {
    if (name in scripts) return name;
  }
  return null;
}

async function runScript(root: string, scriptName: string) {
  const pm = packageManager(root);
  const cmd =
    pm === "pnpm"
      ? ["pnpm", "run", scriptName]
      : pm === "yarn"
        ? ["yarn", scriptName]
        : ["npm", "run", scriptName];
  return execFileAsync(cmd[0], cmd.slice(1), {
    cwd: root,
    timeout: BUILD_TIMEOUT_SEC * 1000,
    maxBuffer: 20 * 1024 * 1024,
  });
}

registerTool({
  name: "detect_framework",
  risk: "read",
  description: "检测工作区项目使用的多端框架（uni-app/Taro/Morjs 等）及可用构建脚本。",
  parameters: { type: "object", properties: {} },
  handler: async () => {
    const root = workspaceRoot();
    const pkg = readPackageJson(root);
    if (!pkg) return toolError("未找到可解析的 package.json");
    const deps = collectDeps(pkg);
    const signals = detectSignals(root, deps);
    const scripts = (pkg.scripts as Record<string, string>) ?? {};
    let framework = "unknown";
    if (signals.includes("taro")) framework = "taro";
    else if (signals.includes("uni-app") || signals.includes("uni-app-like")) framework = "uni-app";
    else if (signals.includes("morjs")) framework = "morjs";
    else if (signals.length) framework = signals[0];
    return toolOk({
      framework,
      signals,
      name: pkg.name,
      package_manager: packageManager(root),
      scripts: Object.keys(scripts),
      suggested_build: Object.fromEntries(
        Object.keys(TARGET_SCRIPTS).map((t) => [t, pickBuildScript(scripts, t)]),
      ),
    });
  },
});

registerTool({
  name: "run_build",
  risk: "exec",
  description: "执行项目构建。target 可选 weixin、alipay、h5、tt、baidu。",
  parameters: {
    type: "object",
    properties: { target: { type: "string" } },
  },
  handler: async (args) => {
    const root = workspaceRoot();
    const pkg = readPackageJson(root);
    if (!pkg) return toolError("未找到 package.json，无法推断构建命令");
    const scripts = (pkg.scripts as Record<string, string>) ?? {};
    const target = String(args.target ?? "weixin").trim().toLowerCase() || "weixin";
    const scriptName = pickBuildScript(scripts, target);
    if (!scriptName) {
      return toolError(`未找到适合 target=${target} 的构建脚本`, {
        available: Object.keys(scripts),
        supported_targets: Object.keys(TARGET_SCRIPTS),
      });
    }
    try {
      const { stdout, stderr } = await runScript(root, scriptName);
      const output = (stdout ?? "") + (stderr ?? "");
      const tail =
        output.length > BUILD_OUTPUT_TAIL ? output.slice(-BUILD_OUTPUT_TAIL) : output;
      return toolOk({
        script: scriptName,
        target,
        package_manager: packageManager(root),
        output: tail,
      });
    } catch (err: unknown) {
      const e = err as { stdout?: string; stderr?: string; code?: number; message?: string };
      const output = (e.stdout ?? "") + (e.stderr ?? "");
      const tail =
        output.length > BUILD_OUTPUT_TAIL ? output.slice(-BUILD_OUTPUT_TAIL) : output;
      return toolError(`构建失败: ${packageManager(root)} run ${scriptName}`, {
        exit_code: e.code,
        output: tail,
      });
    }
  },
});
