# Makefile for managing the uv-based project

.PHONY: setup clean run

# Setup: create/activate .venv and install dependencies with uv
setup:
	uv venv .venv
	uv sync

# Clean: remove virtualenv and clear uv caches
clean:
	@if [ -d .venv ]; then rm -rf .venv; fi
	@if [ -f uv.lock ]; then rm uv.lock; fi
	uv cache clean
	uv cache prune

# Run the FastMCP server
run:
	uv run angelone-mcp