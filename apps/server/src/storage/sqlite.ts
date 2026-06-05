import fs from "node:fs";
import path from "node:path";

import Database from "better-sqlite3";

import { config } from "../config.js";

function nowIso(): string {
  return new Date().toISOString();
}

type TableInfoRow = { name: string };

export class SQLiteStorage {
  private db: Database.Database;

  constructor(dbPath = config.dbPath) {
    fs.mkdirSync(path.dirname(dbPath), { recursive: true });
    this.db = new Database(dbPath);
    this.initSchema();
  }

  private hasColumn(table: string, column: string): boolean {
    const rows = this.db.prepare(`PRAGMA table_info(${table})`).all() as TableInfoRow[];
    return rows.some((row) => row.name === column);
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

    if (!this.hasColumn("sessions", "policy")) {
      this.db.exec(
        `ALTER TABLE sessions ADD COLUMN policy TEXT NOT NULL DEFAULT 'readonly'`,
      );
    }
    if (!this.hasColumn("sessions", "owner_username")) {
      this.db.exec(`ALTER TABLE sessions ADD COLUMN owner_username TEXT`);
    }

    this.db.exec(`
      CREATE TABLE IF NOT EXISTS auth_tokens (
        token TEXT PRIMARY KEY,
        username TEXT NOT NULL,
        expires_at TEXT NOT NULL,
        created_at TEXT NOT NULL
      )
    `);
  }

  createSession(
    sessionId: string,
    name: string,
    policy: string,
    ownerUsername: string | null,
  ): void {
    const ts = nowIso();
    this.db
      .prepare(
        `INSERT INTO sessions (id, name, messages, created_at, updated_at, policy, owner_username)
         VALUES (?, ?, ?, ?, ?, ?, ?)`,
      )
      .run(sessionId, name, "[]", ts, ts, policy, ownerUsername);
  }

  getSessionById(sessionId: string): Record<string, string> | null {
    const row = this.db
      .prepare(
        `SELECT id, name, messages, created_at, updated_at, policy, owner_username
         FROM sessions WHERE id = ?`,
      )
      .get(sessionId) as Record<string, string> | undefined;
    return row ?? null;
  }

  createAuthToken(token: string, username: string, expiresAt: string): void {
    this.db
      .prepare(
        `INSERT INTO auth_tokens (token, username, expires_at, created_at)
         VALUES (?, ?, ?, ?)`,
      )
      .run(token, username, expiresAt, nowIso());
  }

  deleteAuthToken(token: string): void {
    this.db.prepare(`DELETE FROM auth_tokens WHERE token = ?`).run(token);
  }

  getUsernameByToken(token: string): string | null {
    const row = this.db
      .prepare(`SELECT username, expires_at FROM auth_tokens WHERE token = ?`)
      .get(token) as { username: string; expires_at: string } | undefined;
    if (!row) {
      return null;
    }
    if (new Date(row.expires_at).getTime() <= Date.now()) {
      this.deleteAuthToken(token);
      return null;
    }
    return row.username;
  }
}

let storage: SQLiteStorage | null = null;

export function getStorage(): SQLiteStorage {
  if (!storage) storage = new SQLiteStorage();
  return storage;
}
