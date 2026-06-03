"""Demo4: @asynccontextmanager — 等同 stdio_client 结构"""
import asyncio
from contextlib import asynccontextmanager


@asynccontextmanager
async def fake_stdio_client(command: str):
    print(f"  [__aenter__] spawn: {command}")
    read, write = "stdin_stream", "stdout_stream"
    yield read, write
    print("  [__aexit__] 终止子进程")


@asynccontextmanager
async def fake_session(read, write):
    print(f"  [session aenter] 绑定 {read}/{write}")
    yield "session_obj"
    print("  [session aexit] 释放会话")


async def main():
    async with fake_stdio_client("python calc_server.py") as (read, write):
        async with fake_session(read, write) as session:
            print(f"  [块内] await initialize(), session={session}")

    print("=== 全部关闭 ===")


if __name__ == "__main__":
    asyncio.run(main())
