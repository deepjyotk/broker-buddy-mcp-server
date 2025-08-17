from __future__ import annotations

from typing import Any, Dict, List, Union

from fastmcp import Context, FastMCP

from service import get_coinbase_secrets, get_crypto_portfolio
from utils.const import MCPToolsTags

# JSON-like return type without recursive self-references (pydantic-friendly)
JSONValue = Union[None, bool, int, float, str, List[Any], Dict[str, Any]]


def register_coinbase_tools(mcp: FastMCP) -> None:
    """Register Coinbase-related tools.

    Tools:
      - get_portfolio() -> dict: Return Coinbase portfolio summary.
    """

    @mcp.tool(
        name="get_portfolio",
        description=(
            "Return current Coinbase portfolio holdings via Advanced Trade API. "
            "Requires env-based authentication to have been configured."
        ),
        tags=[MCPToolsTags.CRYPTO_EXCHANGE.value, MCPToolsTags.COINBASE_BROKER.value],
    )
    def get_portfolio_tool(ctx: Context) -> JSONValue:
        """Fetch Coinbase portfolio holdings.

        Auth is read from the MCP request context headers via `secret_service`.
        """
        auth_headers = ctx.get_state("auth_headers")
        secret = get_coinbase_secrets(auth_headers.user_id, auth_headers.scopes)
        response = get_crypto_portfolio(secret)
        return response
