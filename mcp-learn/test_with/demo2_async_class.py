"""Demo2: async with — __aenter__ / __aexit__"""
import asyncio


class AsyncSession:
    async def __aenter__(self):
        print("  [__aenter__] 建立会话")
        return self

    async def __aexit__(self, exc_type, exc, tb):
        print("  [__aexit__] 销毁会话")
        return False

    async def call(self, name: str):
        print(f"  [call] {name}")


async def main():
    async with AsyncSession() as session:
        await session.call("initialize")
        await session.call("tools/list")

    print("=== 会话已关 ===")


if __name__ == "__main__":
    asyncio.run(main())
    print("=== 程序已结束 ===")
