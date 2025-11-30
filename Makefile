.PHONY: all proto inference platform frontend dev clean test install help \
        backend-proto backend-inference backend-platform backend-test backend-install backend-clean \
        backend-e2e-test backend-proto-test backend-test-all

# Default target
all: backend-proto backend-platform

# ============================================================================
# Backend (delegates to backend/Makefile)
# ============================================================================

backend-proto:
	@$(MAKE) -C backend proto

backend-inference:
	@$(MAKE) -C backend inference

backend-inference-install:
	@$(MAKE) -C backend inference-install

backend-inference-test:
	@$(MAKE) -C backend inference-test

backend-platform:
	@$(MAKE) -C backend platform

backend-platform-dev:
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

frontend:
	@cd frontend && npm run dev

frontend-build:
	@cd frontend && npm run build

# ============================================================================
# Development
# ============================================================================

dev:
	@echo "Starting all services..."
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
	@./scripts/kill_port.sh 8000
	@./scripts/kill_port.sh 50051
	@echo "Killed processes on ports 8000 and 50051"

# ============================================================================
# Help
# ============================================================================

help:
	@echo "Good Listener - Available Commands"
	@echo ""
	@echo "Setup:"
	@echo "  make install              - Install all dependencies"
	@echo "  make proto                - Generate protobuf files"
	@echo ""
	@echo "Development:"
	@echo "  make dev                  - Start all services"
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
	@echo "  make kill-ports           - Kill processes on ports 8000 and 50051"
