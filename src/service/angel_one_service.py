import datetime as dt
from zoneinfo import ZoneInfo

import pyotp

from SmartApi.smartConnect import SmartConnect

IST = ZoneInfo("Asia/Kolkata")

_session = {"access_token": None, "login_time": None}


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
