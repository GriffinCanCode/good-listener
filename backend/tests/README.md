# Backend Integration Tests

End-to-end tests that verify the full backend stack works together:

- **Proto**: Protobuf definitions compile for both Python and Go
- **Inference**: Python gRPC server serves ML requests
- **Platform**: Go platform connects to inference and orchestrates services

## Running Tests

```bash
# From project root
make backend-e2e-test

# Or from backend/
make e2e-test
```

## Test Structure

- `e2e_test.go` - Go integration tests that spin up Python inference and test full flow
- `test_proto_compat.py` - Python tests for proto compatibility
- `docker-compose.test.yml` - Optional containerized test environment

