class StorageError(Exception):
    """存储层错误。"""


class SessionNotFoundError(StorageError):
    def __init__(self, session_id: str) -> None:
        self.session_id = session_id
        super().__init__(f"找不到会话: {session_id}")
