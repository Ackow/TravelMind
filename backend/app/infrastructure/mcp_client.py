import asyncio
import json
import sys
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


class McpClientAdapter:
    """TravelMind MCP 客户端管理器，负责与独立 MCP 工具微服务建立通信。"""

    def __init__(self, command: str = sys.executable, args: list[str] | None = None) -> None:
        self._command = command
        self._args = args or ["-m", "mcp_server.server"]

    async def call_tool(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """通过 MCP 协议调用远程工具并解析返回结果。"""
        server_params = StdioServerParameters(
            command=self._command,
            args=self._args,
            env=None,
        )

        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                # 1. 协议握手与初始化
                await session.initialize()

                # 2. 发起工具远程调用
                result = await session.call_tool(tool_name, arguments=arguments)

                # 3. 提取内容并反序列化 JSON
                if not result.content:
                    raise RuntimeError(f"MCP 工具 [{tool_name}] 返回空内容")

                raw_text = result.content[0].text
                response_json = json.loads(raw_text) if isinstance(raw_text, str) else raw_text
                if isinstance(response_json, dict) and not response_json.get("success", True):
                    raise RuntimeError(
                        f"MCP 工具 [{tool_name}] 执行失败: {response_json.get('error')}"
                    )

                return (
                    response_json.get("data", response_json)
                    if isinstance(response_json, dict)
                    else response_json
                )

    def call_tool_sync(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """同步包装器，适配同步规划器与防腐层。"""
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            import nest_asyncio

            nest_asyncio.apply()
            return loop.run_until_complete(self.call_tool(tool_name, arguments))

        return asyncio.run(self.call_tool(tool_name, arguments))
