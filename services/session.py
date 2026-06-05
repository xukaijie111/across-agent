import uuid

from services.storage.factory import get_storage

from .storage.base import StorageBackend


PLACEHOLDER_NAME = "untitled"  # 或 "unnamed"


class SessionService:

    def __init__(self, storage: StorageBackend | None = None) -> None:
        self.storage = storage or get_storage()

    def create(self, name: str | None = None) -> str:
        session_id = uuid.uuid4().hex
        if name and name.strip():
            final_name = name.strip()
        else:
            # 多个未命名会话也不会撞 UNIQUE
            final_name = f"{PLACEHOLDER_NAME}-{session_id[:8]}"
        self.storage.create_session(session_id, final_name)

        return session_id

    def get_session(self, session_id: str) -> dict | None:
        return self.storage.get_session_by_id(session_id)

    def list_sessions(self) -> list[dict]:
        return self.storage.list_sessions()

    def exists_session(self, name: str) -> bool:
        return self.storage.get_session_by_name(name) is not None

    def get_history(self, session_id: str) -> list[dict]:
        return self.storage.get_messages(session_id)

    def append_messages(self, session_id: str, messages: list[dict]) -> None:
        self.storage.append_messages(session_id, messages)

    def rename_session_name(self, session_id: str, new_name: str) -> None:
        self.storage.rename_session(session_id, new_name)

    def delete_session(self, session_id: str) -> None:
        self.storage.delete_session(session_id)


session_service = SessionService()
