# Good Listener

A background assistant for macOS that analyzes screen context to provide real-time reports and research.

## Architecture

The application is split into two main components:

1.  **Frontend (Electron + React):**
    *   Handles the UI (modal popup, settings).
    *   Manages the application window state (always on top, hidden/shown).
    *   Communicates with the backend via HTTP/WebSocket.

2.  **Backend (Python FastAPI):**
    *   Runs as a local server.
    *   Handles screen capture (using `mss` or native APIs via `pyobjc`).
    *   Performs OCR and context analysis (Text extraction, keyword detection).
    *   Manages "research" logic (connecting to LLMs or search tools).

## Prerequisites

- Python 3.10+
- Node.js 16+
- Tesseract OCR (optional, depending on OCR choice)

## Setup

### Backend
```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python main.py
```

### Frontend
```bash
cd frontend
npm install
npm start
```

