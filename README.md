# Good Listener

Real-time audio transcription, screen capture, and AI-assisted conversation analysis.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     Go Platform (port 8000)                     │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────────────────┐  │
│  │ Audio Capture│  │ Screen Grab  │  │ WebSocket/HTTP Server │  │
│  │ (malgo)      │  │ (screenshot) │  │ (coder/websocket)     │  │
│  └──────┬───────┘  └──────┬───────┘  └───────────┬───────────┘  │
│         │                 │                      │              │
│         ▼                 ▼                      │              │
│  ┌──────────────────────────────────────┐        │              │
│  │  Orchestrator (channels, backpressure)│◄──────┘              │
│  └──────────────────┬───────────────────┘                       │
└─────────────────────┼───────────────────────────────────────────┘
                      │ gRPC (port 50051)
                      ▼
┌─────────────────────────────────────────────────────────────────┐
│                  Python Inference Services                       │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │ Whisper STT │  │ OCR Service │  │ LLM Service (streaming) │  │
│  │ + Silero VAD│  │ (RapidOCR)  │  │ (Gemini/Ollama)         │  │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘  │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │                Memory Service (ChromaDB)                     ││
│  └─────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────┘
```

## Project Structure

```
good-listener/
├── proto/                    # Protobuf definitions
│   └── cognition.proto
├── inference/                # Python ML services
│   ├── app/
│   │   ├── core/            # Logging, utilities
│   │   ├── services/        # Transcription, VAD, OCR, LLM, Memory
│   │   ├── pb/              # Generated protobuf code
│   │   └── grpc_server.py   # gRPC server entry point
│   ├── tests/
│   └── requirements.txt
├── platform/                 # Go orchestration layer
│   ├── cmd/server/          # Main entry point
│   ├── internal/
│   │   ├── audio/           # Audio capture with backpressure
│   │   ├── screen/          # Screen capture
│   │   ├── orchestrator/    # Service coordination
│   │   ├── server/          # HTTP/WebSocket handlers
│   │   ├── grpcclient/      # gRPC client to Python
│   │   └── config/          # Configuration
│   ├── pkg/pb/              # Generated protobuf code
│   └── go.mod
├── frontend/                 # Electron + React UI
└── Makefile
```

## Quick Start

### Prerequisites

- Go 1.22+
- Python 3.11+
- Node.js 18+
- protoc (Protocol Buffers compiler)

### Installation

```bash
# Install all dependencies
make install

# Generate protobuf files (requires protoc)
make proto
```

### Running

```bash
# Start all services (inference + platform + frontend)
make dev

# Or start individually:
make inference    # Python gRPC server on :50051
make platform     # Go server on :8000
make frontend     # React dev server
```

### Environment Variables

Create a `.env` file in the project root:

```env
# LLM Configuration
GOOGLE_API_KEY=your-api-key
LLM_PROVIDER=gemini
LLM_MODEL=gemini-2.0-flash

# Platform Configuration
HTTP_ADDR=:8000
INFERENCE_ADDR=localhost:50051
SAMPLE_RATE=16000
VAD_THRESHOLD=0.5
CAPTURE_SYSTEM_AUDIO=true
AUTO_ANSWER_ENABLED=true
```

## Development

### Testing

```bash
make test           # All tests
make inference-test # Python tests only
make platform-test  # Go tests only
```

### Proto Regeneration

After modifying `proto/cognition.proto`:

```bash
make proto
```

## Why This Architecture?

1. **Go for orchestration**: Native goroutines + channels provide:
   - Proper backpressure (bounded channels)
   - Graceful cancellation (context)
   - Efficient concurrency without GIL

2. **Python for ML inference**: Keeps the ML ecosystem:
   - PyTorch/faster-whisper for transcription
   - LangChain for LLM abstraction
   - ChromaDB for vector storage

3. **gRPC for communication**:
   - Type-safe API contracts
   - Streaming support for audio/LLM
   - Language-agnostic

## License

MIT
