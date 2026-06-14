"""MySQL 持久化：session、聊天消息、LangGraph checkpoint。"""

from __future__ import annotations

import json
import os
import uuid
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Iterator

import pymysql
from pymysql.cursors import DictCursor

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS agent_sessions (
    session_id VARCHAR(64) PRIMARY KEY,
    agent_id VARCHAR(64) NOT NULL,
    user_id VARCHAR(64) NOT NULL DEFAULT '',
    title VARCHAR(255) NOT NULL DEFAULT '',
    state_json JSON NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_agent_user_updated (agent_id, user_id, updated_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS chat_messages (
    message_id VARCHAR(64) PRIMARY KEY,
    session_id VARCHAR(64) NOT NULL,
    role VARCHAR(16) NOT NULL,
    content TEXT NOT NULL,
    meta_json JSON NULL,
    seq INT NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_session_seq (session_id, seq),
    CONSTRAINT fk_chat_session FOREIGN KEY (session_id) REFERENCES agent_sessions(session_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS lg_checkpoints (
    thread_id VARCHAR(64) NOT NULL,
    checkpoint_ns VARCHAR(255) NOT NULL DEFAULT '',
    checkpoint_id VARCHAR(64) NOT NULL,
    parent_checkpoint_id VARCHAR(64) NULL,
    type VARCHAR(64) NULL,
    checkpoint LONGBLOB NULL,
    metadata LONGBLOB NULL,
    PRIMARY KEY (thread_id, checkpoint_ns, checkpoint_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS lg_writes (
    thread_id VARCHAR(64) NOT NULL,
    checkpoint_ns VARCHAR(255) NOT NULL DEFAULT '',
    checkpoint_id VARCHAR(64) NOT NULL,
    task_id VARCHAR(64) NOT NULL,
    idx INT NOT NULL,
    channel VARCHAR(255) NOT NULL,
    type VARCHAR(64) NULL,
    value LONGBLOB NULL,
    PRIMARY KEY (thread_id, checkpoint_ns, checkpoint_id, task_id, idx)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
"""


@dataclass
class SessionRecord:
    session_id: str
    agent_id: str
    user_id: str
    title: str
    state: dict[str, Any]
    created_at: datetime
    updated_at: datetime


@dataclass
class MessageRecord:
    message_id: str
    session_id: str
    role: str
    content: str
    meta: dict[str, Any] | None
    seq: int
    created_at: datetime


_mysql_ready = False


def init_mysql() -> None:
    """启动时连接 MySQL 并建表，失败则直接抛错。"""
    global _mysql_ready
    if _mysql_ready:
        return

    missing = [k for k, v in {
        "MYSQL_HOST": os.getenv("MYSQL_HOST"),
        "MYSQL_DATABASE": os.getenv("MYSQL_DATABASE"),
        "MYSQL_USER": os.getenv("MYSQL_USER"),
    }.items() if not v]
    if missing:
        raise RuntimeError(
            f"缺少 MySQL 配置: {', '.join(missing)}。请在 .env 中配置 MYSQL_HOST / MYSQL_DATABASE / MYSQL_USER"
        )

    try:
        mysql_store.ensure_schema()
    except Exception as exc:
        raise RuntimeError(
            f"MySQL 连接失败 ({os.getenv('MYSQL_HOST')}:{os.getenv('MYSQL_PORT', '3306')}/"
            f"{os.getenv('MYSQL_DATABASE')}): {exc}"
        ) from exc

    _mysql_ready = True


def _mysql_config() -> dict[str, Any]:
    return {
        "host": os.getenv("MYSQL_HOST", "127.0.0.1"),
        "port": int(os.getenv("MYSQL_PORT", "3306")),
        "user": os.getenv("MYSQL_USER", "root"),
        "password": os.getenv("MYSQL_PASSWORD", ""),
        "database": os.getenv("MYSQL_DATABASE", "agent_playground"),
        "charset": "utf8mb4",
        "cursorclass": DictCursor,
        "autocommit": False,
    }


class MySQLStore:
    def __init__(self) -> None:
        self._schema_ready = False

    @contextmanager
    def _conn(self) -> Iterator[pymysql.connections.Connection]:
        conn = pymysql.connect(**_mysql_config())
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _migrate_schema(self, cur: pymysql.cursors.Cursor) -> None:
        cur.execute("SHOW COLUMNS FROM agent_sessions LIKE 'user_id'")
        if not cur.fetchone():
            cur.execute(
                "ALTER TABLE agent_sessions ADD COLUMN user_id VARCHAR(64) NOT NULL DEFAULT '' AFTER agent_id"
            )
            cur.execute(
                "CREATE INDEX idx_agent_user_updated ON agent_sessions (agent_id, user_id, updated_at)"
            )

    def _row_to_session(self, row: dict[str, Any]) -> SessionRecord:
        return SessionRecord(
            session_id=row["session_id"],
            agent_id=row["agent_id"],
            user_id=row.get("user_id") or "",
            title=row["title"] or "",
            state=json.loads(row["state_json"])
            if isinstance(row["state_json"], (str, bytes))
            else row["state_json"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    def ensure_schema(self) -> None:
        if self._schema_ready:
            return
        with self._conn() as conn:
            with conn.cursor() as cur:
                for stmt in SCHEMA_SQL.split(";"):
                    sql = stmt.strip()
                    if sql:
                        cur.execute(sql)
                self._migrate_schema(cur)
        self._schema_ready = True

    def create_session(
        self,
        agent_id: str,
        initial_state: dict[str, Any],
        *,
        user_id: str,
        title: str = "",
        session_id: str | None = None,
    ) -> SessionRecord:
        self.ensure_schema()
        session_id = session_id or uuid.uuid4().hex
        with self._conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO agent_sessions (session_id, agent_id, user_id, title, state_json)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (
                        session_id,
                        agent_id,
                        user_id,
                        title,
                        json.dumps(initial_state, ensure_ascii=False),
                    ),
                )
        now = datetime.utcnow()
        return SessionRecord(
            session_id=session_id,
            agent_id=agent_id,
            user_id=user_id,
            title=title,
            state=initial_state,
            created_at=now,
            updated_at=now,
        )

    def get_session(self, session_id: str) -> SessionRecord | None:
        self.ensure_schema()
        with self._conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT session_id, agent_id, user_id, title, state_json, created_at, updated_at
                    FROM agent_sessions WHERE session_id = %s
                    """,
                    (session_id,),
                )
                row = cur.fetchone()
        if not row:
            return None
        return self._row_to_session(row)

    def update_session_state(self, session_id: str, state: dict[str, Any]) -> None:
        self.ensure_schema()
        with self._conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE agent_sessions SET state_json = %s WHERE session_id = %s",
                    (json.dumps(state, ensure_ascii=False), session_id),
                )

    def touch_session_title(self, session_id: str, title: str) -> None:
        if not title:
            return
        self.ensure_schema()
        with self._conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE agent_sessions SET title = %s WHERE session_id = %s AND (title = '' OR title IS NULL)",
                    (title[:255], session_id),
                )

    def list_sessions(self, agent_id: str, user_id: str, *, limit: int = 30) -> list[SessionRecord]:
        """只返回该用户、有过聊天记录的 session，过滤空会话。"""
        self.ensure_schema()
        with self._conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT s.session_id, s.agent_id, s.user_id, s.title, s.state_json, s.created_at, s.updated_at
                    FROM agent_sessions s
                    INNER JOIN chat_messages m ON m.session_id = s.session_id
                    WHERE s.agent_id = %s AND s.user_id = %s
                    GROUP BY s.session_id, s.agent_id, s.user_id, s.title, s.state_json, s.created_at, s.updated_at
                    ORDER BY s.updated_at DESC
                    LIMIT %s
                    """,
                    (agent_id, user_id, limit),
                )
                rows = cur.fetchall()
        return [self._row_to_session(row) for row in rows]

    def reset_session(self, session_id: str, initial_state: dict[str, Any]) -> SessionRecord | None:
        session = self.get_session(session_id)
        if session is None:
            return None
        self.delete_checkpoint_thread(session_id)
        self.ensure_schema()
        with self._conn() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM chat_messages WHERE session_id = %s", (session_id,))
                cur.execute(
                    "UPDATE agent_sessions SET state_json = %s, title = '' WHERE session_id = %s",
                    (json.dumps(initial_state, ensure_ascii=False), session_id),
                )
        return self.get_session(session_id)

    def delete_checkpoint_thread(self, thread_id: str) -> None:
        self.ensure_schema()
        with self._conn() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM lg_writes WHERE thread_id = %s", (thread_id,))
                cur.execute("DELETE FROM lg_checkpoints WHERE thread_id = %s", (thread_id,))

    def next_message_seq(self, session_id: str) -> int:
        self.ensure_schema()
        with self._conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT COALESCE(MAX(seq), 0) + 1 AS next_seq FROM chat_messages WHERE session_id = %s",
                    (session_id,),
                )
                row = cur.fetchone()
        return int(row["next_seq"])

    def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        *,
        meta: dict[str, Any] | None = None,
        message_id: str | None = None,
    ) -> MessageRecord:
        self.ensure_schema()
        message_id = message_id or uuid.uuid4().hex
        seq = self.next_message_seq(session_id)
        with self._conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO chat_messages (message_id, session_id, role, content, meta_json, seq)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    (
                        message_id,
                        session_id,
                        role,
                        content,
                        json.dumps(meta, ensure_ascii=False) if meta else None,
                        seq,
                    ),
                )
        now = datetime.utcnow()
        return MessageRecord(
            message_id=message_id,
            session_id=session_id,
            role=role,
            content=content,
            meta=meta,
            seq=seq,
            created_at=now,
        )

    def delete_empty_sessions(
        self, agent_id: str, user_id: str, *, keep_session_id: str | None = None
    ) -> None:
        self.ensure_schema()
        with self._conn() as conn:
            with conn.cursor() as cur:
                if keep_session_id:
                    cur.execute(
                        """
                        DELETE s FROM agent_sessions s
                        LEFT JOIN chat_messages m ON m.session_id = s.session_id
                        WHERE s.agent_id = %s
                          AND s.user_id = %s
                          AND s.session_id <> %s
                          AND m.message_id IS NULL
                        """,
                        (agent_id, user_id, keep_session_id),
                    )
                else:
                    cur.execute(
                        """
                        DELETE s FROM agent_sessions s
                        LEFT JOIN chat_messages m ON m.session_id = s.session_id
                        WHERE s.agent_id = %s AND s.user_id = %s AND m.message_id IS NULL
                        """,
                        (agent_id, user_id),
                    )

    def clear_awaiting_messages(self, session_id: str) -> None:
        self.ensure_schema()
        with self._conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE chat_messages
                    SET meta_json = JSON_SET(COALESCE(meta_json, JSON_OBJECT()), '$.awaiting_action', false)
                    WHERE session_id = %s
                      AND JSON_EXTRACT(meta_json, '$.awaiting_action') = true
                    """,
                    (session_id,),
                )

    def list_messages(self, session_id: str) -> list[MessageRecord]:
        self.ensure_schema()
        with self._conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT message_id, session_id, role, content, meta_json, seq, created_at
                    FROM chat_messages
                    WHERE session_id = %s
                    ORDER BY seq ASC
                    """,
                    (session_id,),
                )
                rows = cur.fetchall()
        result: list[MessageRecord] = []
        for row in rows:
            meta_raw = row["meta_json"]
            meta = None
            if meta_raw:
                meta = json.loads(meta_raw) if isinstance(meta_raw, (str, bytes)) else meta_raw
            result.append(
                MessageRecord(
                    message_id=row["message_id"],
                    session_id=row["session_id"],
                    role=row["role"],
                    content=row["content"],
                    meta=meta,
                    seq=row["seq"],
                    created_at=row["created_at"],
                )
            )
        return result


mysql_store = MySQLStore()
