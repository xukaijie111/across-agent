from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from db import MessageRecord, SessionRecord, mysql_store


@dataclass
class Session:
    session_id: str
    agent_id: str
    title: str = ""
    state: dict[str, Any] = field(default_factory=dict)
    updated_at: datetime | None = None


class SessionStore:
    def _bind_thread_id(self, session_id: str, state: dict[str, Any]) -> dict[str, Any]:
        state = dict(state)
        state["thread_id"] = session_id
        return state

    def _to_session(self, record: SessionRecord) -> Session:
        return Session(
            session_id=record.session_id,
            agent_id=record.agent_id,
            title=record.title,
            state=record.state,
            updated_at=record.updated_at,
        )

    def create(self, agent_id: str, initial_state: dict[str, Any], *, title: str = "") -> Session:
        session_id = uuid.uuid4().hex
        state = self._bind_thread_id(session_id, initial_state)
        record = mysql_store.create_session(agent_id, state, title=title)
        mysql_store.delete_empty_sessions(agent_id, keep_session_id=session_id)
        return self._to_session(record)

    def get(self, session_id: str) -> Session | None:
        record = mysql_store.get_session(session_id)
        return self._to_session(record) if record else None

    def update_state(self, session_id: str, state: dict[str, Any]) -> None:
        mysql_store.update_session_state(session_id, state)

    def list_by_agent(self, agent_id: str, *, limit: int = 30) -> list[Session]:
        return [self._to_session(r) for r in mysql_store.list_sessions(agent_id, limit=limit)]

    def reset(self, session_id: str, initial_state: dict[str, Any]) -> Session | None:
        state = self._bind_thread_id(session_id, initial_state)
        record = mysql_store.reset_session(session_id, state)
        return self._to_session(record) if record else None

    def delete(self, session_id: str) -> None:
        mysql_store.delete_checkpoint_thread(session_id)

    def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        *,
        meta: dict[str, Any] | None = None,
        message_id: str | None = None,
    ) -> MessageRecord:
        return mysql_store.add_message(session_id, role, content, meta=meta, message_id=message_id)

    def list_messages(self, session_id: str) -> list[MessageRecord]:
        return mysql_store.list_messages(session_id)

    def clear_awaiting_messages(self, session_id: str) -> None:
        mysql_store.clear_awaiting_messages(session_id)

    def touch_title(self, session_id: str, title: str) -> None:
        mysql_store.touch_session_title(session_id, title)


session_store = SessionStore()
