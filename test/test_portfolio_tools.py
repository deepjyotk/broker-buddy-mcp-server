import pathlib
import sys
from types import SimpleNamespace
from typing import Any, Callable, Dict

# Ensure the project 'src' directory is on sys.path for imports when running tests locally
ROOT_DIR = pathlib.Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))


import pytest  # noqa: E402

from angelone_mcp.tools import portfolio_tools as pt  # noqa: E402


class FakeMCP:
    def __init__(self) -> None:
        self.tools: Dict[str, Callable[..., Any]] = {}

    # Mimic FastMCP.tool decorator
    def tool(
        self, name: str, description: str
    ) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            self.tools[name] = func
            return func

        return decorator


class FakeContext:
    def __init__(self, state: Dict[str, Any] | None = None) -> None:
        self._state = state or {}

    def get_state(self, key: str) -> Any:
        return self._state.get(key)


def _register_and_get_tool() -> tuple[FakeMCP, Callable[..., Any]]:
    mcp = FakeMCP()
    pt.register_portfolio_tools(mcp)  # registers tools into mcp.tools
    tool = mcp.tools.get("get_portfolio_holdings")
    assert tool is not None, "Tool 'get_portfolio_holdings' was not registered"
    return mcp, tool


def test_get_portfolio_holdings_success(monkeypatch: pytest.MonkeyPatch) -> None:
    _, tool = _register_and_get_tool()

    captured_secret_args: list[tuple[str, list[str]]] = []

    def fake_get_secret(user_id: str, scopes: list[str]) -> dict[str, Any]:
        captured_secret_args.append((user_id, scopes))
        return {"token": "secret-token"}

    expected_response = {"status": True, "data": [{"symbol": "AAPL", "qty": 10}]}

    def fake_get_holdings(secret: dict[str, Any]) -> dict[str, Any]:
        assert secret == {"token": "secret-token"}
        return expected_response

    monkeypatch.setattr(pt, "get_secret", fake_get_secret)
    monkeypatch.setattr(pt, "get_holdings", fake_get_holdings)

    auth_headers = SimpleNamespace(user_id="user-123", scopes=["read", "holdings"])
    ctx = FakeContext(state={"auth_headers": auth_headers})

    result = tool(ctx)  # call the registered tool function

    assert result == expected_response
    # Ensure get_secret was called with values from ctx state
    assert captured_secret_args == [
        ("user-123", ["read", "holdings"])
    ], "get_secret not called with expected args"


def test_get_portfolio_holdings_raises_on_error_status(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, tool = _register_and_get_tool()

    monkeypatch.setattr(pt, "get_secret", lambda user_id, scopes: {"token": "t"})

    def fake_get_holdings_error(secret: dict[str, Any]) -> dict[str, Any]:
        return {"status": False, "message": "API down"}

    monkeypatch.setattr(pt, "get_holdings", fake_get_holdings_error)

    auth_headers = SimpleNamespace(user_id="user-err", scopes=["read"])
    ctx = FakeContext(state={"auth_headers": auth_headers})

    with pytest.raises(RuntimeError) as exc:
        tool(ctx)

    assert "holding() failed: API down" in str(exc.value)
