.PHONY: proto proto-python proto-go inference inference-venv inference-test platform platform-deps platform-build platform-dev platform-test e2e-test proto-test clean

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

platform-deps:
	@cd platform && go mod tidy

platform-build:
	@cd platform && go build -o bin/server ./cmd/server

platform: platform-deps platform-build
	@cd platform && ./bin/server

platform-dev:
	@cd platform && go run ./cmd/server

platform-test:
	@cd platform && go test ./...

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

test: inference-test platform-test

test-all: inference-test platform-test proto-test e2e-test
	@echo "All tests passed!"

install: inference-install platform-deps
	@cd tests && go mod tidy

clean:
	@rm -rf inference/venv inference/__pycache__ inference/**/__pycache__
	@rm -rf inference/app/pb/*.py inference/app/pb/__pycache__
	@rm -rf platform/bin
	@echo "Backend cleaned"

