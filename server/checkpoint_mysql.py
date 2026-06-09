"""LangGraph checkpoint 存 MySQL（表 lg_checkpoints / lg_writes）。"""

from __future__ import annotations

import json
import threading
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from typing import Any, cast

from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.base import (
    WRITES_IDX_MAP,
    BaseCheckpointSaver,
    ChannelVersions,
    Checkpoint,
    CheckpointMetadata,
    CheckpointTuple,
    get_checkpoint_id,
    get_checkpoint_metadata,
)

from db import mysql_store


class MysqlSaver(BaseCheckpointSaver[str]):
    def __init__(self) -> None:
        super().__init__()
        self.lock = threading.Lock()
        self.is_setup = False

    def setup(self) -> None:
        if self.is_setup:
            return
        mysql_store.ensure_schema()
        self.is_setup = True

    @contextmanager
    def cursor(self):
        self.setup()
        with mysql_store._conn() as conn:
            with conn.cursor() as cur:
                yield cur

    def get_tuple(self, config: RunnableConfig) -> CheckpointTuple | None:
        checkpoint_ns = config["configurable"].get("checkpoint_ns", "")
        with self.lock:
            with self.cursor() as cur:
                if checkpoint_id := get_checkpoint_id(config):
                    cur.execute(
                        """
                        SELECT thread_id, checkpoint_id, parent_checkpoint_id, type, checkpoint, metadata
                        FROM lg_checkpoints
                        WHERE thread_id = %s AND checkpoint_ns = %s AND checkpoint_id = %s
                        """,
                        (
                            str(config["configurable"]["thread_id"]),
                            checkpoint_ns,
                            checkpoint_id,
                        ),
                    )
                else:
                    cur.execute(
                        """
                        SELECT thread_id, checkpoint_id, parent_checkpoint_id, type, checkpoint, metadata
                        FROM lg_checkpoints
                        WHERE thread_id = %s AND checkpoint_ns = %s
                        ORDER BY checkpoint_id DESC
                        LIMIT 1
                        """,
                        (str(config["configurable"]["thread_id"]), checkpoint_ns),
                    )
                value = cur.fetchone()
                if not value:
                    return None

                thread_id = value["thread_id"]
                checkpoint_id = value["checkpoint_id"]
                parent_checkpoint_id = value["parent_checkpoint_id"]
                type_ = value["type"]
                checkpoint = value["checkpoint"]
                metadata = value["metadata"]

                if not get_checkpoint_id(config):
                    config = {
                        "configurable": {
                            "thread_id": thread_id,
                            "checkpoint_ns": checkpoint_ns,
                            "checkpoint_id": checkpoint_id,
                        }
                    }

                cur.execute(
                    """
                    SELECT task_id, channel, type, value
                    FROM lg_writes
                    WHERE thread_id = %s AND checkpoint_ns = %s AND checkpoint_id = %s
                    ORDER BY task_id, idx
                    """,
                    (
                        str(config["configurable"]["thread_id"]),
                        checkpoint_ns,
                        str(config["configurable"]["checkpoint_id"]),
                    ),
                )
                writes = cur.fetchall()

        return CheckpointTuple(
            config,
            self.serde.loads_typed((type_, checkpoint)),
            cast(CheckpointMetadata, json.loads(metadata) if metadata is not None else {}),
            (
                {
                    "configurable": {
                        "thread_id": thread_id,
                        "checkpoint_ns": checkpoint_ns,
                        "checkpoint_id": parent_checkpoint_id,
                    }
                }
                if parent_checkpoint_id
                else None
            ),
            [
                (row["task_id"], row["channel"], self.serde.loads_typed((row["type"], row["value"])))
                for row in writes
            ],
        )

    def list(
        self,
        config: RunnableConfig | None,
        *,
        filter: dict[str, Any] | None = None,
        before: RunnableConfig | None = None,
        limit: int | None = None,
    ) -> Iterator[CheckpointTuple]:
        _ = (config, filter, before, limit)
        return iter(())

    def put(
        self,
        config: RunnableConfig,
        checkpoint: Checkpoint,
        metadata: CheckpointMetadata,
        new_versions: ChannelVersions,
    ) -> RunnableConfig:
        _ = new_versions
        thread_id = config["configurable"]["thread_id"]
        checkpoint_ns = config["configurable"]["checkpoint_ns"]
        type_, serialized_checkpoint = self.serde.dumps_typed(checkpoint)
        serialized_metadata = json.dumps(
            get_checkpoint_metadata(config, metadata), ensure_ascii=False
        ).encode("utf-8", "ignore")
        with self.lock:
            with self.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO lg_checkpoints
                    (thread_id, checkpoint_ns, checkpoint_id, parent_checkpoint_id, type, checkpoint, metadata)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                    parent_checkpoint_id = VALUES(parent_checkpoint_id),
                    type = VALUES(type),
                    checkpoint = VALUES(checkpoint),
                    metadata = VALUES(metadata)
                    """,
                    (
                        str(config["configurable"]["thread_id"]),
                        checkpoint_ns,
                        checkpoint["id"],
                        config["configurable"].get("checkpoint_id"),
                        type_,
                        serialized_checkpoint,
                        serialized_metadata,
                    ),
                )
        return {
            "configurable": {
                "thread_id": thread_id,
                "checkpoint_ns": checkpoint_ns,
                "checkpoint_id": checkpoint["id"],
            }
        }

    def put_writes(
        self,
        config: RunnableConfig,
        writes: Sequence[tuple[str, Any]],
        task_id: str,
        task_path: str = "",
    ) -> None:
        _ = task_path
        query = (
            """
            INSERT INTO lg_writes
            (thread_id, checkpoint_ns, checkpoint_id, task_id, idx, channel, type, value)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE type = VALUES(type), value = VALUES(value)
            """
            if all(w[0] in WRITES_IDX_MAP for w in writes)
            else """
            INSERT IGNORE INTO lg_writes
            (thread_id, checkpoint_ns, checkpoint_id, task_id, idx, channel, type, value)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """
        )
        with self.lock:
            with self.cursor() as cur:
                for idx, (channel, value) in enumerate(writes):
                    type_, serialized = self.serde.dumps_typed(value)
                    cur.execute(
                        query,
                        (
                            str(config["configurable"]["thread_id"]),
                            str(config["configurable"]["checkpoint_ns"]),
                            str(config["configurable"]["checkpoint_id"]),
                            task_id,
                            WRITES_IDX_MAP.get(channel, idx),
                            channel,
                            type_,
                            serialized,
                        ),
                    )

    def delete_thread(self, thread_id: str) -> None:
        mysql_store.delete_checkpoint_thread(thread_id)
