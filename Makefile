.PHONY: all setup setup-deps setup-verify proto inference platform frontend dev clean test install help \
        backend-proto backend-inference backend-platform backend-test backend-install backend-clean \
        backend-e2e-test backend-proto-test backend-test-all backend-start

# Default target
all: backend-proto backend-platform

# ============================================================================
# Setup (installs all system dependencies)
# ============================================================================

setup:
	@./scripts/setup.sh

setup-deps:
	@./scripts/setup.sh --deps-only

setup-verify:
	@./scripts/setup.sh --verify

# ============================================================================
# Backend (delegates to backend/Makefile)
# ============================================================================

backend-proto:
	@$(MAKE) -C backend proto

backend-inference: kill-ports
	@$(MAKE) -C backend inference

backend-inference-install:
	@$(MAKE) -C backend inference-install

backend-inference-test:
	@$(MAKE) -C backend inference-test

backend-platform: kill-ports
	@$(MAKE) -C backend platform

backend-platform-dev: kill-ports
	@$(MAKE) -C backend platform-dev

backend-platform-test:
	@$(MAKE) -C backend platform-test

backend-test:
	@$(MAKE) -C backend test

backend-e2e-test:
	@$(MAKE) -C backend e2e-test

backend-proto-test:
	@$(MAKE) -C backend proto-test

backend-test-all:
	@$(MAKE) -C backend test-all

backend-install:
	@$(MAKE) -C backend install

backend-clean:
	@$(MAKE) -C backend clean

backend-start: kill-ports
	@$(MAKE) -C backend start

# Aliases for convenience
proto: backend-proto
inference: backend-inference
platform: backend-platform
inference-test: backend-inference-test
platform-test: backend-platform-test

# ============================================================================
# Frontend
# ============================================================================

frontend-install:
	@cd frontend && npm install

frontend: kill-ports
	@cd frontend && npm run dev

frontend-build:
	@cd frontend && npm run build

# ============================================================================
# Development
# ============================================================================

dev: kill-ports
	@echo "Starting all services..."
	@sleep 0.5
	@$(MAKE) -j3 backend-inference backend-platform frontend

install: backend-install frontend-install
	@echo "All dependencies installed"

# ============================================================================
# Testing
# ============================================================================

test: backend-test
	@echo "All tests passed"

test-all: backend-test-all
	@echo "All tests (including e2e) passed"

e2e-test: backend-e2e-test

# ============================================================================
# Utilities
# ============================================================================

clean: backend-clean
	@rm -rf frontend/node_modules frontend/dist
	@echo "Cleaned all build artifacts"

kill-ports:
	@./scripts/kill_port.sh 5173 2>/dev/null || true
	@./scripts/kill_port.sh 8000 2>/dev/null || true
	@./scripts/kill_port.sh 50051 2>/dev/null || true

# ============================================================================
# Help
# ============================================================================

help:
	@echo "Good Listener - Available Commands"
	@echo ""
	@echo "Setup:"
	@echo "  make setup                - Full setup (system deps + project deps)"
	@echo "  make setup-deps           - Install system dependencies only"
	@echo "  make setup-verify         - Verify system dependencies"
	@echo "  make install              - Install project dependencies"
	@echo "  make proto                - Generate protobuf files"
	@echo ""
	@echo "Development:"
	@echo "  make dev                  - Start all services (backend + frontend)"
	@echo "  make backend-start        - Start backend only (inference + platform)"
	@echo "  make inference            - Start Python inference gRPC server (port 50051)"
	@echo "  make platform             - Build and start Go platform server (port 8000)"
	@echo "  make backend-platform-dev - Run Go platform in dev mode"
	@echo "  make frontend             - Start frontend dev server"
	@echo ""
	@echo "Testing:"
	@echo "  make test                 - Run unit tests"
	@echo "  make test-all             - Run all tests including e2e"
	@echo "  make e2e-test             - Run end-to-end integration tests"
	@echo "  make inference-test       - Run Python tests"
	@echo "  make platform-test        - Run Go tests"
	@echo ""
	@echo "Utilities:"
	@echo "  make clean                - Remove build artifacts"
	@echo "  make kill-ports           - Kill processes on ports 5173, 8000, 50051"
