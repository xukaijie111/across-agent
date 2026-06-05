import fs from "node:fs";
import path from "node:path";

import Database from "better-sqlite3";

import { config } from "../config.js";

function nowIso(): string {
  return new Date().toISOString();
}

export class SQLiteStorage {
  private db: Database.Database;

  constructor(dbPath = config.dbPath) {
    fs.mkdirSync(path.dirname(dbPath), { recursive: true });
    this.db = new Database(dbPath);
    this.initSchema();
  }

  private initSchema(): void {
    this.db.exec(`
      CREATE TABLE IF NOT EXISTS sessions (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL UNIQUE,
        messages TEXT NOT NULL DEFAULT '[]',
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
      )
    `);
  }

  createSession(sessionId: string, name: string): void {
    const ts = nowIso();
    this.db
      .prepare(
        `INSERT INTO sessions (id, name, messages, created_at, updated_at)
         VALUES (?, ?, ?, ?, ?)`,
      )
      .run(sessionId, name, "[]", ts, ts);
  }

  getSessionById(sessionId: string): Record<string, string> | null {
    const row = this.db
      .prepare(
        `SELECT id, name, messages, created_at, updated_at FROM sessions WHERE id = ?`,
      )
      .get(sessionId) as Record<string, string> | undefined;
    return row ?? null;
  }
}

let storage: SQLiteStorage | null = null;

export function getStorage(): SQLiteStorage {
  if (!storage) storage = new SQLiteStorage();
  return storage;
}
