# Makefile for managing the uv-based project

.PHONY: setup clean run lint dev-deps pre-commit-install pre-commit-run

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


dev-deps:
	VIRTUAL_ENV= uv add --dev black isort autoflake flake8 pytest pre-commit

# Lint/format the codebase
lint: dev-deps
	uv run --active black .
	uv run --active autoflake --recursive --in-place --remove-all-unused-imports .
	uv run --active isort .

# Install git pre-commit hooks
pre-commit-install: dev-deps
	uv run --active pre-commit install

# Run all pre-commit hooks against the entire repo
pre-commit-run: dev-deps
	uv run --active pre-commit run --all-files