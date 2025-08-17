from __future__ import annotations

from typing import Any, Dict, List, Union

from fastmcp import Context, FastMCP

from dtos.order_params_dto import DeliveryTradeParams
from service.angel_one_service import (
    execute_delivery_trade,
    get_holdings,
)
from service.secret_service import get_angel_one_secrets
from utils.const import MCPToolsTags

# JSON-like return type without recursive self-references (pydantic-friendly)
JSONValue = Union[None, bool, int, float, str, List[Any], Dict[str, Any]]


def register_angel_one_tools(mcp: FastMCP) -> None:
    """Register portfolio-related tools.

    Args:
      mcp: FastMCP server instance to register tools on.
    """

    @mcp.tool(
        name="get_portfolio_holdings",
        description=(
            "Return current portfolio holdings via Smart API. Requires "
            "env-based authentication to have been configured."
        ),
        tags=[MCPToolsTags.INDIAN_EXCHANGE.value, MCPToolsTags.ANGELONE_BROKER.value],
    )
    def get_portfolio_holdings_tool(ctx: Context) -> JSONValue:
        """Fetch portfolio holdings using SmartConnect.holding().

        Returns:
          JSONValue: API response from Smart API `holding()` endpoint.
        Raises:
          RuntimeError: If the underlying API call fails or returns an
          error status.
        """
        # tool_context = mcp.get_context()
        auth_headers = ctx.get_state("auth_headers")
        secret = get_angel_one_secrets(auth_headers.user_id, auth_headers.scopes)
        response = get_holdings(secret)

        # The library generally returns a dict with keys: status, message, data
        if isinstance(response, dict) and response.get("status") is False:
            # Bubble up an error with helpful context
            message = response.get("message", "Unknown error")
            raise RuntimeError(f"holding() failed: {message}")
        return response

    @mcp.tool(
        name="execute_delivery_trade",
        description="Execute a delivery trade",
        tags=[MCPToolsTags.INDIAN_EXCHANGE.value, MCPToolsTags.ANGELONE_BROKER.value],
    )
    def execute_delivery_trade_tool(
        order: DeliveryTradeParams, ctx: Context
    ) -> JSONValue:
        auth_headers = ctx.get_state("auth_headers")
        secret = get_angel_one_secrets(auth_headers.user_id, auth_headers.scopes)
        response = execute_delivery_trade(secret, order)
        if isinstance(response, dict) and response.get("status") is False:
            message = response.get("message", "Unknown error")
            raise RuntimeError(f"execute_delivery_trade failed: {message}")
        return response
