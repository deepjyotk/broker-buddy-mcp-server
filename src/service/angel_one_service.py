import datetime as dt
import logging
import time
from zoneinfo import ZoneInfo

import pyotp
from SmartApi.smartConnect import SmartConnect

from dtos.order_params_dto import DeliveryTradeParams, OrderType

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

        _session["access_token"] = smart.access_token
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


def execute_delivery_trade(secret, order: DeliveryTradeParams):
    """
    Place a DELIVERY (CNC) BUY order using explicit order parameters.

    If `symboltoken` is not provided, it will be resolved via searchScrip
    using the provided `tradingsymbol` and `exchange`.
    """
    logger.info(f"execute_delivery_trade: {order}")
    if SmartConnect is None:
        raise RuntimeError("SmartApi not available: failed to import SmartConnect")

    if not order.tradingsymbol or not str(order.tradingsymbol).strip():
        raise RuntimeError("tradingsymbol must be a non-empty string")
    if order.quantity is None or int(order.quantity) < 1:
        raise RuntimeError("quantity must be a whole number >= 1")
    if not order.transactiontype:
        raise RuntimeError("transactiontype must be provided")

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
        # Persist raw JWT from the active SmartConnect instance
        _session["access_token"] = smart.access_token
        _session["login_time"] = dt.datetime.now(IST)
    else:
        smart = SmartConnect(
            api_key=secret.share_credentials.trading_api_key,
            access_token=_session["access_token"],
        )

    # 2) if symboltoken is none then it means we will default to EQ
    symboltoken = order.symboltoken
    if not order.symboltoken:
        search_resp = smart.searchScrip(order.exchange.value, order.tradingsymbol)
        if isinstance(search_resp, dict) and (
            search_resp.get("code") in (401, "AG8001")
            or "Session" in str(search_resp.get("message", ""))
        ):
            _session["access_token"] = None
            return execute_delivery_trade(secret, order)
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
                if item.get("exchange") == order.exchange.value and str(
                    item.get("tradingsymbol", "")
                ).endswith("-EQ"):
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
        "variety": order.variety.value,
        "tradingsymbol": order.tradingsymbol,
        "symboltoken": str(symboltoken),
        "transactiontype": order.transactiontype.value,
        "exchange": order.exchange.value,
        "ordertype": order.ordertype.value,
        "producttype": order.producttype.value,
        "duration": order.duration.value,
        "price": (
            None if order.ordertype.value == OrderType.MARKET.value else order.price
        ),
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
        return execute_delivery_trade(secret, order)

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
