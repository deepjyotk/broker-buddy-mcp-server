from __future__ import annotations

import logging
import os
import time

from dotenv import load_dotenv
from fastmcp import Context, FastMCP
from fastmcp.exceptions import ToolError
from fastmcp.server.dependencies import get_http_headers
from fastmcp.server.middleware import Middleware, MiddlewareContext

from dtos.auth_headers_dto import AuthHeadersDto
from utils.const import AuthHeadersConstants

load_dotenv()

logger = logging.getLogger(__name__)


class CustomMiddleware(Middleware):
    """
    Injects the user_id into the per-request FastMCP context state so
    tools can read it.
    """

    async def on_message(self, mctx: MiddlewareContext, call_next):
        start_time = time.perf_counter()

        try:
            result = await call_next(mctx)
            return result
        finally:
            end_time = time.perf_counter()
            duration_s = end_time - start_time
            duration_ms = duration_s * 1000
            message = (
                f"[{mctx.type}] {mctx.method} took {duration_s:.3f} s "
                f"({duration_ms:.2f} ms)"
            )
            logger.info(message)
            print(message)

    async def on_call_tool(self, mctx: MiddlewareContext, call_next):

        http_headers = get_http_headers()
        try:
            user_id = http_headers.get(AuthHeadersConstants.USER_ID.value)
            scopes = http_headers.get(AuthHeadersConstants.SCOPES.value)
            if not user_id or not scopes:
                raise ToolError("User ID and scopes are required")

            # convert scopes to list
            scopes = scopes.split(",")

            auth_dto = AuthHeadersDto(
                user_id=user_id,
                scopes=scopes,
            )

            if auth_dto:
                mctx.fastmcp_context.set_state("auth_headers", auth_dto)
            return await call_next(mctx)
        except ToolError as e:
            logger.error(f"Tool error: {e}")
            raise e
        except Exception as e:
            logger.error(f"Error: {e}")
            raise e


def build_mcp(start_time: float) -> FastMCP:
    mcp = FastMCP(name="angelone-mcp")

    # Add middleware (instance, not class)
    mcp.add_middleware(CustomMiddleware())

    from angelone_mcp.tools.external_tools import register_external_tools
    from angelone_mcp.tools.portfolio_tools import register_portfolio_tools

    register_portfolio_tools(mcp)
    register_external_tools(mcp)

    # Simple healthcheck tool
    @mcp.tool(name="tool:health", description="Service health and uptime")
    def health() -> dict[str, float | str]:
        return {
            "service": "angelone-mcp",
            "uptime_seconds": round(time.time() - start_time, 3),
        }

    # Optional: prove middleware works
    @mcp.tool(
        name="tool:whoami",
        description="Return the resolved user id from request headers",
    )
    def whoami(ctx: Context) -> dict[str, str | None]:
        return {"user_id": ctx.get_state("user_id")}

    return mcp


def main() -> None:
    start_time = time.time()
    mcp = build_mcp(start_time)

    # Run MCP server in HTTP transport (Streamable HTTP)
    host = os.getenv("FASTMCP_HOST", "127.0.0.1")
    port_str = os.getenv("FASTMCP_PORT", "9000")  # keep 9000 as your default
    path = os.getenv("FASTMCP_PATH", "/mcp/")

    try:
        port = int(port_str)
    except ValueError as exc:
        raise RuntimeError(f"Invalid FASTMCP_PORT: {port_str}") from exc

    mcp.run(transport="http", host=host, port=port, path=path)


if __name__ == "__main__":
    main()
