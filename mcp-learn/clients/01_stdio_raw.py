
import asyncio

import sys

from pathlib import Path

from mcp.client.stdio import stdio_client
from mcp import ClientSession,StdioServerParameters


ROOT = Path(__file__).resolve().parent.parent


SERVER_PARAMS = StdioServerParameters(
    command=sys.executable,

    args=[str(ROOT / "servers" / "calc_server.py")],
)


async def main():
    async with stdio_client(server=SERVER_PARAMS) as (read, write):
        
        async with ClientSession(read,write) as session:
            await session.initialize()
            print("Connected to server")
            tools = await session.list_tools()
            
            print("\n\n\n")
            print(tools.tools[0].model_dump_json())
            
            result = await session.call_tool("add", {"a": 1, "b": 2})
            
            print("\n\n\n")
            print(result.content)

if __name__ == "__main__":
    asyncio.run(main())