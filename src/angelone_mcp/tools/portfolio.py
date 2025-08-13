from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable, Dict, List, Union
from fastmcp import FastMCP, Context
from angelone_mcp.server import build_mcp
from utils.const import AuthHeadersConstants
from service.secret_service import get_secret
from service.secret_service import get_secret

try:
    # Import at runtime so the tool can instantiate the SDK
    from SmartApi.smartConnect import SmartConnect
except Exception:
    # Defer import error until tool execution for clearer error surface
    SmartConnect = None  # type: ignore
    

# JSON-like return type without recursive self-references (pydantic-friendly)
JSONValue = Union[None, bool, int, float, str, List[Any], Dict[str, Any]]


def register_portfolio_tools(
    mcp: FastMCP
) -> None:
    """Register portfolio-related tools.

    Args:
      mcp: FastMCP server instance to register tools on.
      smart_provider: Zero-arg callable returning an authenticated SmartConnect.
    """

    @mcp.tool(
        name="get_portfolio_holdings",
        description=(
            "Return current portfolio holdings via Smart API. Requires env-based "
            "authentication to have been configured."
        ),
    )
    def get_portfolio_holdings(ctx: Context) -> JSONValue:
        """Fetch portfolio holdings using SmartConnect.holding().

        Returns:
          JSONValue: API response from Smart API `holding()` endpoint.
        Raises:
          RuntimeError: If the underlying API call fails or returns an error status.
        """
        # tool_context = mcp.get_context()
        auth_headers = ctx.get_state("auth_headers")
        user_id = auth_headers.user_id
        scopes = auth_headers.scopes
        secret = get_secret(auth_headers.user_id, auth_headers.scopes)

        if SmartConnect is None:
            raise RuntimeError("SmartApi not available: failed to import SmartConnect")

        # Initialize SmartConnect with the trading API key (private key header)
        smart = SmartConnect(api_key=secret.share_credentials.history_api_key)
        # Login requires (client_code, password/PIN, TOTP)
        smart.generateSession(
            secret.share_credentials.client_code,
            secret.share_credentials.pin,
            secret.share_credentials.totp_secret,
        )
        response = smart.holding()
        # The library generally returns a dict with keys: status, message, data
        if isinstance(response, dict) and response.get("status") is False:
            # Bubble up an error with helpful context
            message = response.get("message", "Unknown error")
            raise RuntimeError(f"holding() failed: {message}")
        return response

