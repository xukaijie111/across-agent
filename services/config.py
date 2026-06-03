"""
项目配置：类里只指定 .env 路径，文件内所有 KEY 自动变成 config.KEY 属性。

用法：
    from services.config import config
    config.OPENAI_API_KEY
    config.CROSSAGENT_STORAGE
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import dotenv_values, load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent


class Config:
    # 只定义这一处：用哪个 .env 文件
    ENV_FILE: Path = PROJECT_ROOT / ".env"

    def __init__(self, env_file: Path | None = None) -> None:
        path = env_file or self.ENV_FILE
        load_dotenv(path)  # 注入 os.environ，其它模块 os.getenv 也能用
        env = dotenv_values(path)
        for key, value in env.items():
            if key:
                object.__setattr__(self, key, value)

    def get(self, key: str, default: str | None = None) -> str | None:
        """取值，支持默认值（.env 里没有的 key）"""
        if hasattr(self, key):
            val = getattr(self, key)
            return val if val is not None else default
        return os.getenv(key, default)

    def as_dict(self) -> dict[str, str | None]:
        """返回 .env 里全部键值"""
        return {k: getattr(self, k) for k in self.keys()}

    def keys(self) -> list[str]:
        return [k for k in self.__dict__ if not k.startswith("_")]

    # ---------- 派生配置（带默认值）----------

    @property
    def storage_backend(self) -> str:
        return (self.get("CROSSAGENT_STORAGE", "sqlite") or "sqlite").lower()

    @property
    def db_path(self) -> Path:
        raw = self.get("CROSSAGENT_DB_PATH", "data/crossagent.db") or "data/crossagent.db"
        p = Path(raw)
        return p if p.is_absolute() else PROJECT_ROOT / p

    @property
    def workspace_root(self) -> Path:
        """Agent 文件/git 工具允许访问的根目录，默认当前工作目录。"""
        raw = self.get("CROSSAGENT_WORKSPACE")
        if raw and str(raw).strip():
            p = Path(raw.strip())
            return p.resolve() if p.is_absolute() else (PROJECT_ROOT / p).resolve()
        return Path.cwd().resolve()


config = Config()
settings = config  # 别名，factory / 旧代码可用 settings.xxx
