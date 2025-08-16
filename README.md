# Angel One MCP Server

A FastMCP server that provides programmatic access to Angel One's Smart API for portfolio management and stock trading. This server exposes trading tools through the Model Context Protocol (MCP), enabling AI assistants and applications to interact with Angel One's brokerage services for portfolio queries, trade execution, and market news aggregation.

## Features

- **Portfolio Management**: View current holdings and portfolio details
- **Trade Execution**: Place delivery (CNC) buy orders with market prices
- **News Aggregation**: Fetch stock news from multiple sources (Google News, Yahoo News, MoneyControl, Economic Times, Business Standard)
- **Authentication**: Secure user-based authentication with scope-based permissions
- **Health Monitoring**: Built-in health check endpoint for service monitoring

## Prerequisites

- Python 3.13+
- [uv](https://docs.astral.sh/uv/) package manager
- Angel One trading account with API access
- Valid Angel One API credentials (API key, client code, PIN, TOTP secret)

## Setup

### 1. Clone and Install Dependencies

```bash
git clone <repository-url>
cd broker-buddy-mcp-server

# Create virtual environment and install dependencies
make setup
```

### 2. Configure Environment Variables

Create a `.env` file in the project root with your Angel One credentials:

```bash
# Angel One API Configuration
ANGEL_ONE_API_KEY=your_api_key_here
ANGEL_ONE_CLIENT_CODE=your_client_code_here
ANGEL_ONE_PIN=your_pin_here
ANGEL_ONE_TOTP_SECRET=your_totp_secret_here

# Optional: Server Configuration
FASTMCP_HOST=127.0.0.1
FASTMCP_PORT=9000
FASTMCP_PATH=/mcp/
```

### 3. Run the Server

```bash
# Start the MCP server
make run

# Or directly with uv
uv run broker-buddy-mcp
```

The server will start on `http://127.0.0.1:9000/mcp/` by default.

## Quick Setup for Cursor IDE

To quickly test the MCP server in Cursor, create or update your `mcp.json` configuration file:

**Location**: `~/.cursor/mcp.json` (macOS/Linux) or `%APPDATA%\Cursor\User\mcp.json` (Windows)

```json
{
  "mcpServers": {
    "broker-buddy-mcp": {
      "transport": "sse",
      "url": "http://127.0.0.1:9000/mcp/",
      "headers": {
        "X-User-Id": "sample-user-123",
        "X-Scopes": "portfolio:read,portfolio:trade"
      }
    }
  }
}
```

After adding this configuration:
1. Restart Cursor
2. Ensure the MCP server is running (`make run`)
3. The Angel One tools should be available in your Cursor AI assistant

## Available Tools

### Portfolio Tools

- **`get_portfolio_holdings`**: Retrieve current portfolio holdings
- **`buy_delivery_trade`**: Place a delivery buy order (simple parameters)
- **`mcp_broker-buddy-mcp_buy_delivery_trade`**: Place a delivery buy order (structured parameters)

### External Tools

- **`scrape_stock_news_summaries`**: Aggregate stock news from multiple Indian financial news sources

### System Tools

- **`tool:health`**: Check server health and uptime

## Authentication & Permissions

The server uses header-based authentication with the following required headers:

- `X-User-Id`: Unique identifier for the user
- `X-Scopes`: Comma-separated list of permissions (e.g., `portfolio:read,portfolio:trade`)

Available scopes:
- `portfolio:read`: View portfolio holdings
- `portfolio:trade`: Execute trades

## Development

### Code Quality

```bash
# Format and lint code
make lint

# Install pre-commit hooks
make pre-commit-install

# Run pre-commit checks
make pre-commit-run
```

### Testing

```bash
# Run tests
uv run pytest

# Run specific test file
uv run pytest test/test_portfolio_tools.py
```

### Clean Environment

```bash
# Remove virtual environment and caches
make clean
```

## Security Notes

- Never commit your `.env` file or API credentials to version control
- Use environment-specific user IDs and scopes in production
- The server requires valid Angel One credentials to function
- All trading operations are logged for audit purposes

## Troubleshooting

### Common Issues

1. **Authentication Errors**: Verify your Angel One API credentials in the `.env` file
2. **Connection Issues**: Ensure the server is running on the correct host/port
3. **Import Errors**: Run `make setup` to ensure all dependencies are installed
4. **Tool Errors**: Check that required headers (`X-User-Id`, `X-Scopes`) are properly set

### Logs

Server logs are written to the `logs/` directory, organized by date. Check these for detailed error information.

## License

MIT License - see LICENSE file for details.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests and linting: `make lint && uv run pytest`
5. Submit a pull request

## Support

For issues related to:
- Angel One API: Check [Angel One Smart API documentation](https://smartapi.angelbroking.com/)
- FastMCP: Check [FastMCP documentation](https://github.com/jlowin/fastmcp)
- This server: Open an issue in this repository
