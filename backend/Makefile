.PHONY: proto proto-python proto-go \
        inference inference-venv inference-test \
        platform platform-deps platform-build platform-dev platform-test platform-lint platform-fmt platform-coverage platform-tools platform-tidy \
        e2e-test proto-test \
        test test-all install clean help \
        lint fmt tools start

# ============================================================================
# Proto Generation
# ============================================================================

proto: proto-python proto-go

proto-python:
	@echo "Generating Python protobuf files..."
	@cd inference && python3 -m grpc_tools.protoc \
		-I../proto \
		--python_out=app/pb \
		--grpc_python_out=app/pb \
		../proto/cognition.proto
	@sed -i '' 's/import cognition_pb2/from app.pb import cognition_pb2/' inference/app/pb/cognition_pb2_grpc.py 2>/dev/null || true

proto-go:
	@echo "Generating Go protobuf files..."
	@protoc --go_out=platform/pkg/pb --go_opt=paths=source_relative \
		--go-grpc_out=platform/pkg/pb --go-grpc_opt=paths=source_relative \
		-I proto proto/cognition.proto

# ============================================================================
# Inference (Python ML Services)
# ============================================================================

inference-venv:
	@cd inference && python3 -m venv venv
	@cd inference && ./venv/bin/pip install --upgrade pip
	@cd inference && ./venv/bin/pip install -r requirements.txt

inference-install: inference-venv

inference:
	@cd inference && ./venv/bin/python -m app.grpc_server

inference-test:
	@cd inference && ./venv/bin/pytest tests/ -v

# ============================================================================
# Platform (Go Orchestration)
# ============================================================================

# Install Go tooling
platform-tools:
	@echo "Installing Go tools..."
	@go install github.com/golangci/golangci-lint/v2/cmd/golangci-lint@latest
	@go install golang.org/x/tools/cmd/goimports@latest
	@go install github.com/evilmartians/lefthook@latest
	@go install google.golang.org/protobuf/cmd/protoc-gen-go@latest
	@go install google.golang.org/grpc/cmd/protoc-gen-go-grpc@latest
	@cd platform && lefthook install || true
	@echo "Go tools installed"

platform-deps: platform-tidy

platform-tidy:
	@cd platform && go mod tidy

platform-build:
	@cd platform && CGO_ENABLED=1 go build -o server ./cmd/server

platform: platform-deps platform-build
	@cd platform && ./server

platform-dev:
	@cd platform && go run ./cmd/server

# Testing
platform-test:
	@cd platform && go test -race -shuffle=on ./...

platform-test-v:
	@cd platform && go test -race -shuffle=on -v ./...

platform-coverage:
	@cd platform && go test -race -coverprofile=coverage.out -covermode=atomic ./...
	@cd platform && go tool cover -func=coverage.out
	@cd platform && go tool cover -html=coverage.out -o coverage.html
	@echo "Coverage report: platform/coverage.html"

platform-bench:
	@cd platform && go test -bench=. -benchmem ./...

# Linting & Formatting
platform-lint:
	@cd platform && golangci-lint run

platform-lint-fix:
	@cd platform && golangci-lint run --fix

platform-fmt:
	@cd platform && gofmt -s -w .
	@cd platform && goimports -local github.com/good-listener -w .

platform-vet:
	@cd platform && go vet ./...

# Security & Quality
platform-vuln:
	@cd platform && go run golang.org/x/vuln/cmd/govulncheck@latest ./...

platform-mod-verify:
	@cd platform && go mod verify

# ============================================================================
# End-to-End Tests
# ============================================================================

e2e-test:
	@echo "Running end-to-end integration tests..."
	@cd tests && INTEGRATION_TEST=1 go test -v -timeout 120s

proto-test:
	@echo "Running proto compatibility tests..."
	@cd inference && ./venv/bin/python ../tests/test_proto_compat.py

# ============================================================================
# Combined
# ============================================================================

start:
	@echo "Starting backend (inference + platform)..."
	@$(MAKE) -j2 inference platform

test: inference-test platform-test

test-all: inference-test platform-test proto-test e2e-test
	@echo "All tests passed!"

lint: platform-lint
fmt: platform-fmt
tools: platform-tools

install: inference-install platform-deps platform-tools
	@cd tests && go mod tidy

clean:
	@rm -rf inference/venv inference/__pycache__ inference/**/__pycache__
	@rm -rf inference/app/pb/*.py inference/app/pb/__pycache__
	@rm -rf platform/server platform/coverage.out platform/coverage.html
	@echo "Backend cleaned"

# ============================================================================
# Help
# ============================================================================

help:
	@echo "Backend Makefile Commands"
	@echo ""
	@echo "Proto:"
	@echo "  proto              - Generate all protobuf files"
	@echo "  proto-python       - Generate Python protobuf files"
	@echo "  proto-go           - Generate Go protobuf files"
	@echo ""
	@echo "Inference (Python):"
	@echo "  inference          - Run Python inference server"
	@echo "  inference-install  - Install Python dependencies"
	@echo "  inference-test     - Run Python tests"
	@echo ""
	@echo "Platform (Go):"
	@echo "  platform           - Build and run Go server"
	@echo "  platform-dev       - Run Go server in dev mode"
	@echo "  platform-build     - Build Go binary"
	@echo "  platform-test      - Run Go tests"
	@echo "  platform-coverage  - Generate coverage report"
	@echo "  platform-bench     - Run benchmarks"
	@echo "  platform-lint      - Run golangci-lint"
	@echo "  platform-lint-fix  - Auto-fix lint issues"
	@echo "  platform-fmt       - Format Go code"
	@echo "  platform-vet       - Run go vet"
	@echo "  platform-vuln      - Check for vulnerabilities"
	@echo "  platform-tools     - Install Go dev tools"
	@echo ""
	@echo "Combined:"
	@echo "  start              - Start backend (inference + platform)"
	@echo "  test               - Run unit tests"
	@echo "  test-all           - Run all tests"
	@echo "  lint               - Run all linters"
	@echo "  fmt                - Format all code"
	@echo "  tools              - Install all dev tools"
	@echo "  install            - Install all dependencies"
	@echo "  clean              - Clean build artifacts"
