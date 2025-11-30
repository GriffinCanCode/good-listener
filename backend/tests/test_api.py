"""Tests for REST API endpoints."""
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from fastapi import FastAPI
from fastapi.testclient import TestClient
from PIL import Image


@pytest.fixture
def api_client():
    """Create isolated test client with mocked monitor."""
    from app.routers.api import router
    from app.core.schemas import CaptureResponse, RecordingStatusResponse
    
    app = FastAPI()
    app.include_router(router)
    
    mock_monitor = MagicMock()
    mock_monitor.latest_text = "Screen text content"
    mock_monitor.latest_image = Image.new('RGB', (100, 100))
    mock_monitor.set_recording = MagicMock()
    mock_monitor.capture_service = MagicMock()
    
    app.state.monitor = mock_monitor
    
    return TestClient(app), mock_monitor


class TestCaptureEndpoint:
    """Tests for /api/capture endpoint."""

    def test_capture_success(self, api_client):
        """GET /api/capture returns extracted text."""
        client, mock_monitor = api_client
        mock_monitor.latest_text = "Screen text content"
        
        response = client.get("/api/capture")
        
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Screen processed"
        assert "Screen text content" in data["extracted_text"]

    def test_capture_no_image(self, api_client):
        """GET /api/capture triggers capture when no image cached."""
        client, mock_monitor = api_client
        mock_monitor.latest_image = None
        mock_monitor.latest_text = ""
        
        response = client.get("/api/capture")
        
        assert response.status_code == 200
        mock_monitor.capture_service.capture_screen.assert_called_once()

    def test_capture_truncates_long_text(self, api_client):
        """GET /api/capture truncates text > 500 chars."""
        client, mock_monitor = api_client
        mock_monitor.latest_text = "x" * 600
        
        response = client.get("/api/capture")
        
        data = response.json()
        assert len(data["extracted_text"]) <= 503  # 500 + "..."
        assert data["extracted_text"].endswith("...")


class TestRecordingEndpoints:
    """Tests for recording control endpoints."""

    def test_start_recording(self, api_client):
        """POST /api/recording/start enables recording."""
        client, mock_monitor = api_client
        
        response = client.post("/api/recording/start")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "recording_started"
        mock_monitor.set_recording.assert_called_once_with(True)

    def test_stop_recording(self, api_client):
        """POST /api/recording/stop disables recording."""
        client, mock_monitor = api_client
        
        response = client.post("/api/recording/stop")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "recording_stopped"
        mock_monitor.set_recording.assert_called_once_with(False)


class TestHealthEndpoint:
    """Tests for health check (if exists)."""

    def test_root_redirect_or_404(self, api_client):
        """Root endpoint behavior."""
        client, _ = api_client
        response = client.get("/")
        # FastAPI returns 404 by default for undefined routes
        assert response.status_code in [200, 404, 307]


class TestAPIRouter:
    """Tests for API router configuration."""

    def test_api_prefix(self, api_client):
        """API routes use /api prefix."""
        client, _ = api_client
        response = client.get("/api/capture")
        assert response.status_code == 200

    def test_non_api_route_404(self, api_client):
        """Non-API routes return 404."""
        client, _ = api_client
        response = client.get("/capture")
        assert response.status_code == 404

