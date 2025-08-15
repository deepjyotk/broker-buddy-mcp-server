from __future__ import annotations

from typing import Any, Dict, List, Union

from fastmcp import Context, FastMCP

from dtos.order_params_dto import BuyDeliveryOrderParams
from service.angel_one_service import (
    buy_delivery_trade,
    buy_delivery_trade_with_order_params,
    get_holdings,
)
from service.secret_service import get_secret

# JSON-like return type without recursive self-references (pydantic-friendly)
JSONValue = Union[None, bool, int, float, str, List[Any], Dict[str, Any]]


def register_portfolio_tools(mcp: FastMCP) -> None:
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
    )
    def get_portfolio_holdings(ctx: Context) -> JSONValue:
        """Fetch portfolio holdings using SmartConnect.holding().

        Returns:
          JSONValue: API response from Smart API `holding()` endpoint.
        Raises:
          RuntimeError: If the underlying API call fails or returns an
          error status.
        """
        # tool_context = mcp.get_context()
        auth_headers = ctx.get_state("auth_headers")
        secret = get_secret(auth_headers.user_id, auth_headers.scopes)
        response = get_holdings(secret)

        # The library generally returns a dict with keys: status, message, data
        if isinstance(response, dict) and response.get("status") is False:
            # Bubble up an error with helpful context
            message = response.get("message", "Unknown error")
            raise RuntimeError(f"holding() failed: {message}")
        return response

    @mcp.tool(
        name="buy_delivery_trade",
        description=(
            "Place a delivery (CNC) market BUY order for a specified quantity. "
            "Arguments: share_name (str), share_quantity_to_buy (int - shares). "
            "Requires env-based authentication to be configured."
        ),
    )
    def buy_delivery_trade_tool(
        ctx: Context, share_name: str, share_quantity_to_buy: int
    ) -> JSONValue:
        """Buy delivery shares using an explicit share quantity.

        Args:
          share_name: Scrip search text (e.g., "RELIANCE", "TCS").
          share_quantity_to_buy: Number of shares to buy (whole number >= 1).
        """
        auth_headers = ctx.get_state("auth_headers")
        secret = get_secret(auth_headers.user_id, auth_headers.scopes)
        response = buy_delivery_trade(secret, share_name, share_quantity_to_buy)
        if isinstance(response, dict) and response.get("status") is False:
            message = response.get("message", "Unknown error")
            raise RuntimeError(f"buy_delivery_trade failed: {message}")
        return response

    @mcp.tool(
        name="mcp_angelone-mcp_buy_delivery_trade",
        description=(
            "Place a delivery (CNC) market BUY order using structured params. "
            "Takes a Pydantic model with defaults; only `tradingsymbol` and "
            "`quantity` are required."
        ),
    )
    def buy_delivery_trade_with_model(
        order: BuyDeliveryOrderParams, ctx: Context
    ) -> JSONValue:
        auth_headers = ctx.get_state("auth_headers")
        secret = get_secret(auth_headers.user_id, auth_headers.scopes)
        response = buy_delivery_trade_with_order_params(secret, order)
        if isinstance(response, dict) and response.get("status") is False:
            message = response.get("message", "Unknown error")
            raise RuntimeError(f"buy_delivery_trade failed: {message}")
        return response
