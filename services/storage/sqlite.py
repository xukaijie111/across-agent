


from __future__ import annotations
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from .base import StorageBackend




def _now() -> str:
    return datetime.now(timezone.utc).isoformat()

class SQLiteStorage(StorageBackend):
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()
    
    
    def _init_schema(self)->None:
        with self._connect() as conn:
            conn.execute("""
                         CREATE TABLE IF NOT EXISTS sessions(
                             id TEXT PRIMARY KEY,
                             name TEXT NOT NULL UNIQUE,
                             messages TEXT NOT NULL DEFAULT '[]',
                            
                             created_at TEXT NOT NULL,
                             updated_at TEXT NOT NULL
                             
                         )
                         """)
            
   
   
    def _connect(self)->sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    
    def _fetchone(self, sql: str, params: tuple = ())->sqlite3.Row | None:
        with self._connect() as conn:
            return conn.execute(sql, params).fetchone()
    
    def _fetchall(self, sql: str, params: tuple = ())->list[sqlite3.Row] | None:
        with self._connect() as conn:
            return conn.execute(sql, params).fetchall()
    
    def _execute(self, sql: str, params: tuple = ())->None:
        with self._connect() as conn:
            conn.execute(sql, params)
            
    def _row_to_dict(self, row: sqlite3.Row)->dict | None:
       return dict(row) if row else None
   
    def _rows_to_dicts(self, rows: list[sqlite3.Row])->list[dict]:
       return [dict(r) for r in rows] if rows else []
   
   
   
    def create_session(self, session_id: str, name: str)->None:
       self._execute("""
                     INSERT INTO sessions (id, name, messages, created_at, updated_at)
                     VALUES (?, ?, ?, ?, ?)
                     """, (session_id, name, json.dumps([]), _now(), _now()))
       
    def get_session_by_id(self, session_id: str)->dict | None:
    
        session = self._fetchone("""
                                SELECT id, name, messages, created_at, updated_at
                                FROM sessions
                                WHERE id = ?
                                """, (session_id,))
        return self._row_to_dict(session)
    
    def get_session_by_name(self, name: str)->dict | None:
        session = self._fetchone("""
                                SELECT id, name, messages, created_at, updated_at
                                FROM sessions
                                WHERE name = ?
                                """, (name,))
        return self._row_to_dict(session)
    
    def list_sessions(self)->list[dict]:
        sessions = self._fetchall("""
                                SELECT id, name, created_at, updated_at
                                FROM sessions
                                """)
        return self._rows_to_dicts(sessions)
    
    def get_messages(self, session_id: str)->list[dict]:
        row = self._fetchone("""
                                SELECT messages FROM sessions WHERE id = ?
                                """, (session_id,))
        return json.loads(row["messages"]) if row else []
    
    def append_messages(self, session_id: str, messages: list[dict])->None:
        current = self.get_messages(session_id)
        current.extend(messages)
        self._execute("""
                      UPDATE sessions SET messages = ? WHERE id = ?
                      """, (json.dumps(current), session_id))
    
    def rename_session(self, session_id: str, new_name: str)->None:
        self._execute("""
                      UPDATE sessions SET name = ? WHERE id = ?
                      """, (new_name, session_id))
    
    def delete_session(self, session_id: str)->None:
        self._execute("""
                      DELETE FROM sessions WHERE id = ?
                      """, (session_id,))