import datetime as dt
import logging
import time
from zoneinfo import ZoneInfo

import pyotp

from dtos.order_params_dto import BuyDeliveryOrderParams
from SmartApi.smartConnect import SmartConnect

IST = ZoneInfo("Asia/Kolkata")

_session = {"access_token": None, "login_time": None}
logger = logging.getLogger(__name__)


def _next_reset_after(t: dt.datetime) -> dt.datetime:
    # SmartAPI tokens reset at 05:00 IST daily
    five_am_today = t.replace(hour=5, minute=0, second=0, microsecond=0)
    return (
        five_am_today if t < five_am_today else (five_am_today + dt.timedelta(days=1))
    )


def _session_valid() -> bool:
    if not _session["access_token"] or not _session["login_time"]:
        return False
    now = dt.datetime.now(IST)
    return now < _next_reset_after(_session["login_time"])


def get_holdings(secret):
    if SmartConnect is None:
        raise RuntimeError("SmartApi not available: failed to import SmartConnect")

    if not _session_valid():
        smart = SmartConnect(
            api_key=secret.share_credentials.trading_api_key
        )  # use trading key
        totp = pyotp.TOTP(secret.share_credentials.totp_secret).now()
        data = smart.generateSession(
            secret.share_credentials.client_code,
            secret.share_credentials.pin,
            totp,
        )
        if not data or not data.get("status"):
            msg = data.get("message") if isinstance(data, dict) else str(data)
            raise RuntimeError(f"login failed: {msg}")
        _session["access_token"] = data["data"]["jwtToken"]
        _session["login_time"] = dt.datetime.now(IST)
    else:
        smart = SmartConnect(
            api_key=secret.share_credentials.trading_api_key,
            access_token=_session["access_token"],
        )

    resp = smart.holding()

    # If session expired mid-call, force relogin once and retry
    if isinstance(resp, dict) and (
        resp.get("code") in (401, "AG8001") or "Session" in str(resp.get("message", ""))
    ):
        _session["access_token"] = None  # invalidate and recurse once
        return get_holdings(secret)

    if isinstance(resp, dict) and resp.get("status") is False:
        err = resp.get("message", "Unknown error")
        raise RuntimeError(f"holding() failed: {err}")
    return resp


def _retrieve_order_status_from_smartapi(
    smart: SmartConnect,
    order_resp: dict,
    max_attempts: int = 5,
    sleep_seconds: float = 0.6,
) -> tuple[str | None, dict | None]:
    """Retrieve the newly placed order's status and details.

    Uses Individual Order Details API by uniqueorderid with a short retry,
    and falls back to scanning the order book by uniqueorderid/orderid.
    Returns a tuple of (order_status, order_status_details).
    """
    unique_order_id = None
    order_id = None
    try:
        data_block = order_resp.get("data") or {}
        unique_order_id = data_block.get("uniqueorderid")
        order_id = data_block.get("orderid")
    except Exception:  # noqa: BLE001 - defensive
        pass

    order_status_details = None
    last_error_message = None

    for _ in range(max_attempts):
        # Preferred: individual_order_details via uniqueorderid
        if unique_order_id:
            try:
                details_resp = smart.individual_order_details(unique_order_id)
            except Exception as exc:  # noqa: BLE001 - library may raise
                last_error_message = str(exc)
                details_resp = None

            if isinstance(details_resp, dict):
                if details_resp.get("status") is True and details_resp.get("data"):
                    order_status_details = details_resp.get("data")
                    break
                # Some deployments may not include top-level status here
                data_candidate = details_resp.get("data")
                if data_candidate:
                    order_status_details = data_candidate
                    break
                last_error_message = details_resp.get("message") or last_error_message

        # Fallback: scan order book for this order
        try:
            ob_resp = smart.orderBook()
        except Exception as exc:  # noqa: BLE001
            last_error_message = str(exc)
            ob_resp = None

        if isinstance(ob_resp, dict) and ob_resp.get("status") is True:
            orders = ob_resp.get("data") or []
            match = None
            for item in orders:
                try:
                    if unique_order_id and item.get("uniqueorderid") == unique_order_id:
                        match = item
                        break
                    if order_id and str(item.get("orderid")) == str(order_id):
                        match = item
                        break
                except Exception:  # noqa: BLE001
                    continue
            if match is not None:
                order_status_details = match
                break

        time.sleep(sleep_seconds)

    if order_status_details is None and last_error_message:
        logger.warning(f"Unable to fetch order status: {last_error_message}")

    order_status = (
        order_status_details.get("orderstatus")
        if isinstance(order_status_details, dict)
        else None
    )

    return order_status, order_status_details


def buy_delivery_trade(secret, share_name: str, share_quantity_to_buy: float):
    """Place a delivery (cash-and-carry) BUY market order for a given equity.

    Args:
        secret: UserSecret with Angel One credentials.
        share_name: Human-friendly scrip query (e.g., "TCS" or "RELIANCE").
        share_quantity_to_buy: Number of shares to buy (must be a whole number >= 1).

    Returns:
        The SmartAPI order placement response (full response dict).

    Raises:
        RuntimeError: On login failure, scrip lookup failure, or invalid quantity.
    """
    if SmartConnect is None:
        raise RuntimeError("SmartApi not available: failed to import SmartConnect")

    if not share_name or not str(share_name).strip():
        raise RuntimeError("share_name must be a non-empty string")
    try:
        qty_float = float(share_quantity_to_buy)
    except Exception:  # noqa: BLE001 - strict numeric validation
        raise RuntimeError("share_quantity_to_buy must be a number")
    if qty_float <= 0:
        raise RuntimeError("share_quantity_to_buy must be >= 1")
    if int(qty_float) != qty_float:
        raise RuntimeError("share_quantity_to_buy must be a whole number of shares")
    quantity = int(qty_float)

    # 1) Ensure authenticated SmartConnect session
    if not _session_valid():
        smart = SmartConnect(api_key=secret.share_credentials.trading_api_key)
        totp = pyotp.TOTP(secret.share_credentials.totp_secret).now()
        data = smart.generateSession(
            secret.share_credentials.client_code,
            secret.share_credentials.pin,
            totp,
        )
        if not data or not data.get("status"):
            msg = data.get("message") if isinstance(data, dict) else str(data)
            raise RuntimeError(f"login failed: {msg}")
        _session["access_token"] = data["data"]["jwtToken"]
        _session["login_time"] = dt.datetime.now(IST)
    else:
        smart = SmartConnect(
            api_key=secret.share_credentials.trading_api_key,
            access_token=_session["access_token"],
        )

    exchange = "NSE"

    # 2) Find the tradingsymbol and token via searchScrip
    search_resp = smart.searchScrip(exchange, share_name)
    if isinstance(search_resp, dict) and (
        search_resp.get("code") in (401, "AG8001")
        or "Session" in str(search_resp.get("message", ""))
    ):
        _session["access_token"] = None
        return buy_delivery_trade(secret, share_name, share_quantity_to_buy)
    if not isinstance(search_resp, dict) or not search_resp.get("status"):
        msg = (
            search_resp.get("message")
            if isinstance(search_resp, dict)
            else "Unknown error"
        )
        raise RuntimeError(f"searchScrip() failed: {msg}")
    results = search_resp.get("data") or []
    if not results:
        raise RuntimeError("No matching scrip found for the provided share_name")

    # Prefer NSE equity symbols ending with -EQ
    chosen = None
    for item in results:
        try:
            if item.get("exchange") == exchange and str(
                item.get("tradingsymbol", "")
            ).endswith("-EQ"):
                chosen = item
                break
        except Exception:  # noqa: BLE001 - defensive
            continue
    if chosen is None:
        chosen = results[0]

    tradingsymbol = chosen.get("tradingsymbol")
    symboltoken = chosen.get("symboltoken")
    if not tradingsymbol or not symboltoken:
        raise RuntimeError("searchScrip() returned invalid symbol data")

    # 3) We directly place order with the requested quantity (no LTP-based sizing)

    # 4) Place a MARKET order with producttype DELIVERY (CNC)
    orderparams = {
        "variety": "NORMAL",
        "tradingsymbol": tradingsymbol,
        "symboltoken": str(symboltoken),
        "transactiontype": "BUY",
        "exchange": exchange,
        "ordertype": "MARKET",
        "producttype": "DELIVERY",
        "duration": "DAY",
        "price": None,  # MARKET order
        "squareoff": "0",
        "stoploss": "0",
        "quantity": str(quantity),
    }

    order_resp = smart.placeOrderFullResponse(orderparams)
    if isinstance(order_resp, dict) and (
        order_resp.get("code") in (401, "AG8001")
        or "Session" in str(order_resp.get("message", ""))
    ):
        _session["access_token"] = None
        return buy_delivery_trade(secret, share_name, share_quantity_to_buy)

    if order_resp.get("status") is False or order_resp.get("error") is not None:
        raise RuntimeError(f"buy_delivery_trade failed: {order_resp.get('message')}")

    logger.info(f"order_resp: {order_resp}")

    # Fetch order status using a helper (tries individual order details,
    # then order book)
    try:
        order_status, order_status_details = _retrieve_order_status_from_smartapi(
            smart, order_resp
        )
    except Exception as exc:  # noqa: BLE001 - don't fail the primary order call
        logger.error(f"Error while fetching order status: {exc}")
        order_status, order_status_details = None, None

    final_order_resp = {
        "order_id": (order_resp.get("data") or {}).get("orderid"),
        "order_status": order_status,
        "order_status_details": order_status_details,
    }

    # Return the original placement response enhanced with order status details
    return final_order_resp


def buy_delivery_trade_with_order_params(secret, order: BuyDeliveryOrderParams):
    """Place a DELIVERY (CNC) BUY order using explicit order parameters.

    If `symboltoken` is not provided, it will be resolved via searchScrip
    using the provided `tradingsymbol` and `exchange`.
    """
    if SmartConnect is None:
        raise RuntimeError("SmartApi not available: failed to import SmartConnect")

    if not order.tradingsymbol or not str(order.tradingsymbol).strip():
        raise RuntimeError("tradingsymbol must be a non-empty string")
    if order.quantity is None or int(order.quantity) < 1:
        raise RuntimeError("quantity must be a whole number >= 1")

    # 1) Ensure authenticated SmartConnect session
    if not _session_valid():
        smart = SmartConnect(api_key=secret.share_credentials.trading_api_key)
        totp = pyotp.TOTP(secret.share_credentials.totp_secret).now()
        data = smart.generateSession(
            secret.share_credentials.client_code,
            secret.share_credentials.pin,
            totp,
        )
        if not data or not data.get("status"):
            msg = data.get("message") if isinstance(data, dict) else str(data)
            raise RuntimeError(f"login failed: {msg}")
        _session["access_token"] = data["data"]["jwtToken"]
        _session["login_time"] = dt.datetime.now(IST)
    else:
        smart = SmartConnect(
            api_key=secret.share_credentials.trading_api_key,
            access_token=_session["access_token"],
        )

    # 2) Resolve symboltoken when not provided
    symboltoken = order.symboltoken
    exchange = order.exchange
    if not symboltoken:
        search_resp = smart.searchScrip(exchange, order.tradingsymbol)
        if isinstance(search_resp, dict) and (
            search_resp.get("code") in (401, "AG8001")
            or "Session" in str(search_resp.get("message", ""))
        ):
            _session["access_token"] = None
            return buy_delivery_trade_with_order_params(secret, order)
        if not isinstance(search_resp, dict) or not search_resp.get("status"):
            msg = (
                search_resp.get("message")
                if isinstance(search_resp, dict)
                else "Unknown error"
            )
            raise RuntimeError(f"searchScrip() failed: {msg}")
        results = search_resp.get("data") or []
        if not results:
            raise RuntimeError(
                "No matching scrip found to resolve symboltoken for the provided "
                "tradingsymbol"
            )

        chosen = None
        for item in results:
            try:
                if (
                    item.get("exchange") == exchange
                    and str(item.get("tradingsymbol", "")) == order.tradingsymbol
                ):
                    chosen = item
                    break
            except Exception:
                continue
        if chosen is None:
            chosen = results[0]
        symboltoken = chosen.get("symboltoken")
        if not symboltoken:
            raise RuntimeError("searchScrip() returned invalid symbol data")

    # 3) Build order params
    orderparams = {
        "variety": order.variety,
        "tradingsymbol": order.tradingsymbol,
        "symboltoken": str(symboltoken),
        "transactiontype": order.transactiontype,
        "exchange": exchange,
        "ordertype": order.ordertype,
        "producttype": order.producttype,
        "duration": order.duration,
        "price": None if order.ordertype == "MARKET" else order.price,
        "squareoff": order.squareoff,
        "stoploss": order.stoploss,
        "quantity": str(int(order.quantity)),
    }

    order_resp = smart.placeOrderFullResponse(orderparams)
    if isinstance(order_resp, dict) and (
        order_resp.get("code") in (401, "AG8001")
        or "Session" in str(order_resp.get("message", ""))
    ):
        _session["access_token"] = None
        return buy_delivery_trade_with_order_params(secret, order)

    if order_resp.get("status") is False or order_resp.get("error") is not None:
        raise RuntimeError(f"buy_delivery_trade failed: {order_resp.get('message')}")

    logger.info(f"order_resp: {order_resp}")

    # 4) Fetch order status
    try:
        order_status, order_status_details = _retrieve_order_status_from_smartapi(
            smart, order_resp
        )
    except Exception as exc:
        logger.error(f"Error while fetching order status: {exc}")
        order_status, order_status_details = None, None

    final_order_resp = {
        "order_id": (order_resp.get("data") or {}).get("orderid"),
        "order_status": order_status,
        "order_status_details": order_status_details,
    }

    return final_order_resp
