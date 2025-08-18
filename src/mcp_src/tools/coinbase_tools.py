from __future__ import annotations

from typing import Any, Dict, List, Union

from fastmcp import Context, FastMCP

from dtos.crypto_order_dto import ExecuteCryptoTradeParams
from service import get_coinbase_secrets, get_crypto_portfolio
from service.coinbase_service import execute_crypto_trade as svc_execute_crypto_trade
from service.coinbase_service import get_crypto_products as svc_get_crypto_products
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

    @mcp.tool(
        name="list_coinbase_products",
        description=(
            """List tradable Coinbase products (markets)
            and provide a flat list of product IDs."""
        ),
        tags=[MCPToolsTags.CRYPTO_EXCHANGE.value, MCPToolsTags.COINBASE_BROKER.value],
    )
    async def list_coinbase_products_tool(ctx: Context) -> JSONValue:
        """Return Coinbase products and a helper
        list of product IDs for subsequent trades."""
        auth_headers = ctx.get_state("auth_headers")

        # Note: Removed unused elicit call as it's not needed for listing products
        secret = get_coinbase_secrets(auth_headers.user_id, auth_headers.scopes)
        return svc_get_crypto_products(secret)

    @mcp.tool(
        name="execute_crypto_trade",
        description=(
            "Place an order on Coinbase Advanced Trade. "
            "Supports market IOC, limit GTC, and limit GTD."
        ),
        tags=[MCPToolsTags.CRYPTO_EXCHANGE.value, MCPToolsTags.COINBASE_BROKER.value],
    )
    async def execute_crypto_trade_tool(
        order: ExecuteCryptoTradeParams, ctx: Context
    ) -> JSONValue:
        """Execute a Coinbase order using authenticated credentials from context."""
        auth_headers = ctx.get_state("auth_headers")
        secret = get_coinbase_secrets(auth_headers.user_id, auth_headers.scopes)

        if order.side == "SELL":
            if (
                order.order_configuration.market_market_ioc is None
                or order.order_configuration.market_market_ioc.base_size is None
                or order.order_configuration.market_market_ioc.base_size == 0
            ):

                portfolio = get_crypto_portfolio(secret)

                available_value = 0
                for i in range(len(portfolio["holdings"])):
                    if (
                        portfolio["holdings"][i]["currency"]
                        == order.product_id.split("-")[0]
                    ):
                        available_value = portfolio["holdings"][i]["available_value"]
                        break

                prompt = f"""Current you have
                {available_value} in {order.product_id}. Please
                provide the base size for the sell order.
                (Note: Base size is the amount of the base
                currency you want to sell. For example, if
                you want to sell 5 USDC, you need to provide 5)
                """
                # ctx.sample
                result = await ctx.elicit(message=prompt, response_type=float)

                if result.action == "accept":
                    order.order_configuration.market_market_ioc.base_size = result.data
                    order.order_configuration.market_market_ioc.quote_size = None
                else:
                    return "User rejected the request"

        products = svc_get_crypto_products(secret)

        if order.product_id not in products:
            elicit_result = await ctx.elicit(
                message=(
                    f"Product {order.product_id} not found in coinbase. "
                    f"Please provide a valid product id from: {str(products)}"
                ),
                response_type=str,
            )
            if elicit_result.action == "accept":
                order.product_id = elicit_result.data
                if order.product_id not in products:
                    return (
                        "Sorry, the product: "
                        + order.product_id
                        + " is not available on coinbase."
                    )
        else:
            result = await svc_execute_crypto_trade(secret, order)
            return result
