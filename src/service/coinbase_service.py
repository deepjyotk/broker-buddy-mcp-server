from __future__ import annotations

import logging
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

from coinbase.rest import RESTClient

from configs.angel_one_secrets import UserSecret
from dtos.crypto_order_dto import ExecuteCryptoTradeParams

logger = logging.getLogger(__name__)


def _create_rest_client(secret: UserSecret) -> RESTClient:
    if (
        secret.share_credentials_coinbase is None
        or secret.share_credentials_coinbase.api_key is None
        or secret.share_credentials_coinbase.api_secret is None
    ):
        raise RuntimeError("Missing Coinbase API credentials (api_key/api_secret)")

    return RESTClient(
        api_key=secret.share_credentials_coinbase.api_key,
        api_secret=secret.share_credentials_coinbase.api_secret,
    )


def _to_decimal(value: Optional[str]) -> Decimal:
    if value is None or value == "":
        return Decimal("0")
    try:
        return Decimal(str(value))
    except Exception:
        return Decimal("0")


def __list_all_accounts(client: RESTClient, limit: int = 250) -> List[Dict[str, Any]]:
    """Fetch all accounts via pagination from Coinbase Advanced Trade API.

    Returns a list of plain dicts (SDK objects converted via `to_dict()` when
    present) for uniform downstream processing.
    """
    accounts_accum: List[Dict[str, Any]] = []
    cursor: Optional[str] = None

    while True:
        page = client.get_accounts(limit=limit, cursor=cursor)
        page_dict: Dict[str, Any]
        page_dict = page.to_dict() if hasattr(page, "to_dict") else page

        accounts = page_dict.get("accounts", []) or []
        for acc in accounts:
            accounts_accum.append(acc)

        has_next: bool = bool(page_dict.get("has_next"))
        cursor = page_dict.get("cursor")
        if not has_next:
            break

    return accounts_accum


def build_portfolio_summary(
    raw_accounts: List[Dict[str, Any]], product_id: Optional[str] = None
) -> Dict[str, Any]:
    """Transform Coinbase `accounts` into a concise portfolio summary.

    Filters out entries where both available and hold balances are truly zero
    (keeps entries with any non-zero balance).
    """
    holdings: List[Dict[str, Any]] = []

    for acc in raw_accounts:

        uuid = acc.get("uuid", "")
        name = acc.get("name", "")
        currency = acc.get("currency", "")
        platform = acc.get("platform")
        retail_portfolio_id = acc.get("retail_portfolio_id")

        available_balance = acc.get("available_balance") or {}
        hold_balance = acc.get("hold") or {}

        available_val = str(available_balance.get("value", "0"))
        available_ccy = str(available_balance.get("currency", currency or ""))

        hold_val = str(hold_balance.get("value", "0"))
        hold_ccy = str(hold_balance.get("currency", currency or ""))

        is_nonzero = (_to_decimal(available_val) != Decimal("0")) or (
            _to_decimal(hold_val) != Decimal("0")
        )
        if not is_nonzero:
            continue

        holdings.append(
            {
                "uuid": uuid,
                "name": name,
                "currency": currency,
                "available_value": available_val,
                "available_currency": available_ccy,
                "hold_value": hold_val,
                "hold_currency": hold_ccy,
                "platform": platform,
                "retail_portfolio_id": retail_portfolio_id,
            }
        )

    result = {
        "accounts": raw_accounts,
        "has_more": False,
        "holdings": holdings,
        "cursor": None,
        "has_more": False,
    }

    return result


def get_crypto_portfolio(
    secret: Any, product_id: Optional[str] = None
) -> Dict[str, Any]:
    """Return the authenticated user's Coinbase portfolio summary.

    This is a thin wrapper combining client creation, account pagination, and
    summary transformation. Intended to be called by the MCP tool layer.
    """
    client = _create_rest_client(secret)
    accounts = __list_all_accounts(client)
    return build_portfolio_summary(accounts, product_id)


def __list_all_products(
    client: RESTClient, product_type: str = "SPOT", limit: int = 250
) -> List[Any]:
    """Fetch all products via pagination from Coinbase Advanced Trade API.

    Args:
        client: Authenticated REST client.
        product_type: Filter, typically 'SPOT'.
        limit: Page size for pagination.

    Returns:
        List of product dicts.
    """
    products_accum: List[Dict[str, Any]] = []
    cursor: Optional[str] = None

    while True:
        page = client.get_products(
            product_type=product_type, limit=limit, cursor=cursor
        )
        page_dict: Dict[str, Any]
        page_dict = page.to_dict() if hasattr(page, "to_dict") else page

        products = page_dict.get("products", []) or []
        for prod in products:
            products_accum.append(prod)

        has_next: bool = bool(page_dict.get("has_next"))
        cursor = page_dict.get("cursor")
        if not has_next:
            break

    logger.info(f"🔍 Successfully fetched {len(products_accum)} products")
    logger.debug(f"🔍 Products: {products_accum}")
    final_products_ids = []
    for i in range(len(products_accum)):
        final_products_ids.append(products_accum[i]["product_id"])
    return final_products_ids


def get_crypto_products(secret: Any) -> Dict[str, Any]:
    """Return Coinbase products and a simple list of valid `product_id`s."""
    client = _create_rest_client(secret)
    products = __list_all_products(client)
    return products


async def execute_crypto_trade(
    secret: UserSecret, params: ExecuteCryptoTradeParams
) -> Dict[str, Any]:
    """Create an order via Coinbase Advanced Trade API.

    Args:
        secret: User secret containing Coinbase API credentials.
        params: Validated order parameters.

    Returns:
        Plain dict of the order creation response (SDK objects converted when needed).
    """
    client = _create_rest_client(secret)

    # Build order_configuration
    order_configuration: Dict[str, Any]
    if params.order_configuration.market_market_ioc is not None:
        market_cfg = params.order_configuration.market_market_ioc
        cfg: Dict[str, str] = {}
        if market_cfg.base_size is not None:
            cfg["base_size"] = str(market_cfg.base_size)
        if market_cfg.quote_size is not None:
            cfg["quote_size"] = str(market_cfg.quote_size)
        order_configuration = {"market_market_ioc": cfg}
    elif params.order_configuration.limit_limit_gtc is not None:
        limit_cfg = params.order_configuration.limit_limit_gtc
        order_configuration = {
            "limit_limit_gtc": {
                "base_size": str(limit_cfg.base_size),
                "limit_price": str(limit_cfg.limit_price),
                "post_only": bool(limit_cfg.post_only),
            }
        }
    elif params.order_configuration.limit_limit_gtd is not None:
        limit_gtd = params.order_configuration.limit_limit_gtd
        end_time: datetime = limit_gtd.end_time
        order_configuration = {
            "limit_limit_gtd": {
                "base_size": str(limit_gtd.base_size),
                "limit_price": str(limit_gtd.limit_price),
                "end_time": end_time.isoformat().replace("+00:00", "Z"),
                "post_only": bool(limit_gtd.post_only),
            }
        }
    else:
        # Should never happen due to validation
        raise RuntimeError("Invalid order configuration")

    # Ensure a client_order_id is always provided (required by Coinbase SDK)
    generated_client_order_id: str = params.client_order_id or f"mcp-{uuid.uuid4()}"

    payload: Dict[str, Any] = {
        "product_id": params.product_id,
        "side": params.side.value,
        "order_configuration": order_configuration,
        "client_order_id": generated_client_order_id,
    }

    if params.dry_run:
        return {"dry_run": True, "payload": payload}

    # Submit order
    response = client.create_order(**payload)  # type: ignore[arg-type]
    if hasattr(response, "to_dict"):
        return response.to_dict()  # type: ignore[no-any-return]
    if isinstance(response, dict):
        return response
    # Fallback: convert to string
    return {"raw": str(response)}
