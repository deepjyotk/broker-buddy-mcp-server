from __future__ import annotations

from typing import Any, Dict, List, Union

from fastmcp import Context, FastMCP

from service.angel_one_service import get_holdings
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
