import { config as loadEnv } from "dotenv";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
export const PROJECT_ROOT = path.resolve(__dirname, "../../..");

loadEnv({ path: path.join(PROJECT_ROOT, ".env") });

function env(key: string, fallback?: string): string {
  const value = process.env[key] ?? fallback;
  if (value === undefined) {
    throw new Error(`Missing env: ${key}`);
  }
  return value;
}

function envOptional(key: string, fallback = ""): string {
  return process.env[key] ?? fallback;
}

function resolveDataPath(raw: string): string {
  return path.isAbsolute(raw) ? raw : path.join(PROJECT_ROOT, raw);
}

const rawDb = envOptional("CROSSAGENT_DB_PATH", "data/crossagent.db");
const dbPath = resolveDataPath(rawDb);

/** LangGraph checkpoint 单独库：Python(msgpack) 与 TS(json) 不能共用同一 checkpoint 表 */
const rawCheckpointDb = envOptional(
  "CROSSAGENT_CHECKPOINT_DB_PATH",
  "data/crossagent-ts-checkpoints.db",
);
const checkpointDbPath = resolveDataPath(rawCheckpointDb);

const rawWorkspace = envOptional("CROSSAGENT_WORKSPACE");
const workspaceRoot = rawWorkspace.trim()
  ? path.resolve(
      path.isAbsolute(rawWorkspace)
        ? rawWorkspace
        : path.join(PROJECT_ROOT, rawWorkspace),
    )
  : process.cwd();

export const config = {
  openaiApiKey: env("OPENAI_API_KEY"),
  openaiBaseUrl: env("OPENAI_BASE_URL"),
  openaiModel: env("OPENAI_MODEL"),
  dbPath,
  checkpointDbPath,
  workspaceRoot,
  port: Number(envOptional("PORT", "8000")),
  authUsername: envOptional("CROSSAGENT_AUTH_USER", "xukaijie"),
  authPassword: envOptional("CROSSAGENT_AUTH_PASSWORD", "123456"),
};
