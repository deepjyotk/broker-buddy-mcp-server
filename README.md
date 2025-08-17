# Broker Buddy MCP Server

FastMCP server exposing brokerage and market tools (Angel One, Coinbase, News) via the Model Context Protocol (MCP).

## Tools

- **Angel One**:
  - `get_portfolio_holdings`
  - `execute_delivery_trade`
- **Coinbase**:
  - `get_portfolio`
- **External**:
  - `scrape_stock_news_summaries`
- **System**:
  - `tool:health`

## Quick setup

1) Prereqs: Python 3.13+ and `uv`.
2) Install:
```bash
git clone <repository-url>
cd broker-buddy-mcp-server
make setup
```
3) Run:
```bash
make run
# or
uv run broker-buddy-mcp
```
Default: `http://127.0.0.1:9000/mcp/`.

### Required headers
- `x-user-id`: unique user id
- `x-scopes`: comma-separated scopes (e.g., `portfolio:read,portfolio:trade`)

## .env example
Create a `.env` in the repo root. See `src/configs/angel_one_secrets.py` for full field docs.

```bash
# ---- Angel One (required) ----
ANGELONE_HISTORY_API_KEY=...
ANGELONE_HISTORY_SECRET_KEY=...
ANGELONE_TRADING_API_KEY=...
ANGELONE_TRADING_SECRET_KEY=...
ANGELONE_TOTP_SECRET=...
ANGELONE_CLIENT_CODE=...
ANGELONE_PIN=...
# Optional (for eDIS flows)
# ANGELONE_DP_ID=
# ANGELONE_BO_ID=

# ---- Coinbase (if using Coinbase tools) ----
COINBASE_API_KEY=...
COINBASE_API_SECRET=...

# ---- Server (optional) ----
FASTMCP_HOST=127.0.0.1
FASTMCP_PORT=9000
FASTMCP_PATH=/mcp/

# Hide tools by tags (optional, comma-separated). Leave empty to show all.
EXCLUDE_TOOLS_TAGS=
```

## Cursor config (optional)
Add to `~/.cursor/mcp.json`:
```json
{
  "mcpServers": {
    "broker-buddy-mcp": {
      "transport": "http",
      "url": "http://127.0.0.1:9000/mcp/",
      "headers": {
        "x-user-id": "sample-user-123",
        "x-scopes": "portfolio:read,portfolio:trade"
      }
    }
  }
}
```

## Notes
- Keep your `.env` private; never commit secrets.
- Scopes control access; set minimally required scopes.
