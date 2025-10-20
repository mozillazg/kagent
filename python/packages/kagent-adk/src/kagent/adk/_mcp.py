"""Custom MCP integrations for KAgent."""
from __future__ import annotations

from typing import List, Optional

from google.adk.auth.auth_credential import AuthCredential
from google.adk.tools.base_tool import BaseTool
from google.adk.tools.base_toolset import ReadonlyContext
from google.adk.tools.mcp_tool.mcp_session_manager import retry_on_closed_resource
from google.adk.tools.mcp_tool.mcp_tool import MCPTool as BaseMCPTool
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset as BaseMCPToolset
from mcp.types import ListToolsResult
from typing_extensions import override

from ._headers import get_forwarded_headers


def _merge_header(
    headers: Optional[dict[str, str]], header_name: str, header_value: Optional[str]
) -> Optional[dict[str, str]]:
    """Returns headers updated with ``header_name`` set to ``header_value``."""
    if not header_value:
        return headers

    merged = dict(headers) if headers else {}
    merged[header_name] = str(header_value)
    return merged


class KAgentMCPTool(BaseMCPTool):
    """Extends the default MCP tool to forward KAgent-specific headers."""

    @override
    async def _get_headers(
        self,
        tool_context,
        credential: AuthCredential,
    ) -> Optional[dict[str, str]]:
        headers = await super()._get_headers(tool_context, credential)
        if tool_context is None:
            return headers

        state = getattr(tool_context, "state", None)
        if state is None:
            return headers

        merged = headers
        for forwarded in get_forwarded_headers():
            value = state.get(forwarded.state_key)
            merged = _merge_header(merged, forwarded.name, value)
        return merged


class KAgentMCPToolset(BaseMCPToolset):
    """MCP toolset that returns header-aware MCP tools."""

    @override
    @retry_on_closed_resource
    async def get_tools(
        self, readonly_context: Optional[ReadonlyContext] = None
    ) -> List[BaseTool]:
        session = await self._mcp_session_manager.create_session()
        tools_response: ListToolsResult = await session.list_tools()

        tools: List[BaseTool] = []
        for tool in tools_response.tools:
            mcp_tool = KAgentMCPTool(
                mcp_tool=tool,
                mcp_session_manager=self._mcp_session_manager,
                auth_scheme=self._auth_scheme,
                auth_credential=self._auth_credential,
            )
            if self._is_tool_selected(mcp_tool, readonly_context):
                tools.append(mcp_tool)

        return tools
