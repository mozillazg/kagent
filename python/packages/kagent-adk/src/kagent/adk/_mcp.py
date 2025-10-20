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

from ._constants import X_FOO_BAR_HEADER_NAME, X_FOO_BAR_SESSION_STATE_KEY


def _merge_foo_bar_header(
    headers: Optional[dict[str, str]], value: Optional[str]
) -> Optional[dict[str, str]]:
    """Returns headers updated with the foo-bar value when present."""
    if not value:
        return headers

    merged = dict(headers) if headers else {}
    merged[X_FOO_BAR_HEADER_NAME] = str(value)
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
        foo_bar_value = None
        if tool_context is not None:
            # ToolContext.state exposes ``get`` for convenient lookup.
            state = getattr(tool_context, "state", None)
            if state is not None:
                foo_bar_value = state.get(X_FOO_BAR_SESSION_STATE_KEY)
        return _merge_foo_bar_header(headers, foo_bar_value)


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
