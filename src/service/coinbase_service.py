from __future__ import annotations

import logging
from decimal import Decimal
from typing import Any, Dict, List, Optional

from coinbase.rest import RESTClient

from configs.angel_one_secrets import UserSecret

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


def build_portfolio_summary(raw_accounts: List[Dict[str, Any]]) -> Dict[str, Any]:
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


def get_crypto_portfolio(secret: Any) -> Dict[str, Any]:
    """Return the authenticated user's Coinbase portfolio summary.

    This is a thin wrapper combining client creation, account pagination, and
    summary transformation. Intended to be called by the MCP tool layer.
    """
    client = _create_rest_client(secret)
    accounts = __list_all_accounts(client)
    return build_portfolio_summary(accounts)
