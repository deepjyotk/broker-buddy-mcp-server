# Makefile for managing the uv-based project

# Docker image configuration
IMAGE_NAME := broker-buddy-mcp
REGISTRY := # Set this to your registry (e.g., ghcr.io/username, docker.io/username)
VERSION := $(shell git describe --tags --always --dirty 2>/dev/null || echo "dev")
COMMIT_SHA := $(shell git rev-parse --short HEAD 2>/dev/null || echo "unknown")
BUILD_DATE := $(shell date -u +"%Y-%m-%dT%H:%M:%SZ")
PLATFORMS := linux/amd64,linux/arm64

.PHONY: setup clean run lint test test-coverage dev-deps pre-commit-install pre-commit-run
.PHONY: docker-build docker-build-multi docker-push docker-build-and-push docker-clean docker-run

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
	echo "Cleaned up successfully, Deactivate the venv using 'deactivate'"

# Run the FastMCP server
run:
	uv run broker-buddy-mcp


dev-deps:
	VIRTUAL_ENV= uv add --dev black isort autoflake flake8 pytest pytest-cov pre-commit

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

# Run all tests
test: dev-deps
	@echo "Running all tests..."
	uv run --active pytest test/ -v

# Run tests with coverage report
test-coverage: dev-deps
	@echo "Running tests with coverage report..."
	uv run --active pytest test/ -v --cov=src --cov-report=term-missing --cov-report=html
	@echo "Coverage report generated in htmlcov/index.html"

# =============================================================================
# Docker Build Targets
# =============================================================================

# Build single-platform Docker image (current architecture)
docker-build:
	@echo "Building Docker image for current platform..."
	@echo "Version: $(VERSION)"
	@echo "Commit: $(COMMIT_SHA)"
	@echo "Build Date: $(BUILD_DATE)"
	docker build \
		--build-arg VERSION=$(VERSION) \
		--build-arg COMMIT_SHA=$(COMMIT_SHA) \
		--build-arg BUILD_DATE=$(BUILD_DATE) \
		--tag $(IMAGE_NAME):$(VERSION) \
		--tag $(IMAGE_NAME):latest \
		$(if $(REGISTRY),--tag $(REGISTRY)/$(IMAGE_NAME):$(VERSION)) \
		$(if $(REGISTRY),--tag $(REGISTRY)/$(IMAGE_NAME):latest) \
		.

# Build multi-platform Docker image (ARM64 + AMD64)
docker-build-multi:
	@echo "Building multi-platform Docker image..."
	@echo "Platforms: $(PLATFORMS)"
	@echo "Version: $(VERSION)"
	@echo "Commit: $(COMMIT_SHA)"
	@echo "Build Date: $(BUILD_DATE)"
	docker buildx create --use --name multi-arch-builder --driver docker-container || true
	docker buildx build \
		--platform $(PLATFORMS) \
		--build-arg VERSION=$(VERSION) \
		--build-arg COMMIT_SHA=$(COMMIT_SHA) \
		--build-arg BUILD_DATE=$(BUILD_DATE) \
		--tag $(IMAGE_NAME):$(VERSION) \
		--tag $(IMAGE_NAME):latest \
		$(if $(REGISTRY),--tag $(REGISTRY)/$(IMAGE_NAME):$(VERSION)) \
		$(if $(REGISTRY),--tag $(REGISTRY)/$(IMAGE_NAME):latest) \
		--load \
		.

# Push Docker image to registry
docker-push:
	@if [ -z "$(REGISTRY)" ]; then \
		echo "Error: REGISTRY not set. Use: make docker-push REGISTRY=your-registry"; \
		exit 1; \
	fi
	@echo "Pushing to registry: $(REGISTRY)"
	docker push $(REGISTRY)/$(IMAGE_NAME):$(VERSION)
	docker push $(REGISTRY)/$(IMAGE_NAME):latest

# Build multi-platform and push to registry
docker-build-and-push:
	@if [ -z "$(REGISTRY)" ]; then \
		echo "Error: REGISTRY not set. Use: make docker-build-and-push REGISTRY=your-registry"; \
		exit 1; \
	fi
	@echo "Building and pushing multi-platform image..."
	@echo "Platforms: $(PLATFORMS)"
	@echo "Version: $(VERSION)"
	@echo "Registry: $(REGISTRY)"
	docker buildx create --use --name multi-arch-builder --driver docker-container || true
	docker buildx build \
		--platform $(PLATFORMS) \
		--build-arg VERSION=$(VERSION) \
		--build-arg COMMIT_SHA=$(COMMIT_SHA) \
		--build-arg BUILD_DATE=$(BUILD_DATE) \
		--tag $(REGISTRY)/$(IMAGE_NAME):$(VERSION) \
		--tag $(REGISTRY)/$(IMAGE_NAME):latest \
		--push \
		.

# Clean up Docker artifacts for this project only
docker-clean:
	@echo "Cleaning up Docker artifacts for $(IMAGE_NAME)..."
	@echo "Stopping and removing containers..."
	docker ps -q --filter "name=broker-buddy-mcp-container" | xargs -r docker stop
	@echo "Removing project images..."
	docker images "$(IMAGE_NAME)" -q | xargs -r docker rmi -f
	docker images "$(IMAGE_NAME):$(VERSION)" -q | xargs -r docker rmi -f
	docker buildx rm multi-arch-builder || true
	@echo "Clean up complete!"

# Run Docker container in detached mode
docker-run:
	@echo "Running Docker container in detached mode..."
	@echo "Image: $(IMAGE_NAME):latest"
	@echo "Port mapping: 9000:9000"
	docker run -d \
		--name broker-buddy-mcp-container \
		--rm \
		-p 9000:9000 \
		-v "$(PWD)/logs:/app/logs" \
		-v "$(PWD)/.env:/app/.env:ro" \
		--env-file .env \
		-e FASTMCP_HOST=0.0.0.0 \
		$(IMAGE_NAME):latest
	@echo "Container started successfully!"
	@echo "Access the service at: http://localhost:9000"
	@echo "View logs with: docker logs broker-buddy-mcp-container"
	@echo "Stop container with: docker stop broker-buddy-mcp-container"

# Show current build configuration
docker-info:
	@echo "=== Docker Build Configuration ==="
	@echo "Image Name: $(IMAGE_NAME)"
	@echo "Registry: $(if $(REGISTRY),$(REGISTRY),<not set>)"
	@echo "Version: $(VERSION)"
	@echo "Commit SHA: $(COMMIT_SHA)"
	@echo "Build Date: $(BUILD_DATE)"
	@echo "Platforms: $(PLATFORMS)"
	@echo "=================================="