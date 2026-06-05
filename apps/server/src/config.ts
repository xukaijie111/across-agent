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

const rawDb = envOptional("CROSSAGENT_DB_PATH", "data/crossagent.db");
const dbPath = path.isAbsolute(rawDb)
  ? rawDb
  : path.join(PROJECT_ROOT, rawDb);

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
  workspaceRoot,
  port: Number(envOptional("PORT", "8000")),
};
