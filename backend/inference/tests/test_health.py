"""Tests for health check service."""

from unittest.mock import MagicMock

import pytest
from grpc_health.v1 import health_pb2

from app.services.health import HealthServicer, create_health_servicer


class TestHealthServicer:
    def test_initial_status_serving(self):
        servicer = HealthServicer()
        request = MagicMock(service="")
        response = servicer.Check(request, None)
        assert response.status == health_pb2.HealthCheckResponse.SERVING

    def test_unknown_service(self):
        servicer = HealthServicer()
        request = MagicMock(service="unknown.Service")
        response = servicer.Check(request, None)
        assert response.status == health_pb2.HealthCheckResponse.SERVICE_UNKNOWN

    def test_register_checker_healthy(self):
        servicer = HealthServicer()
        servicer.register_checker("test.Service", lambda: True)
        servicer.check_all()
        request = MagicMock(service="test.Service")
        response = servicer.Check(request, None)
        assert response.status == health_pb2.HealthCheckResponse.SERVING

    def test_register_checker_unhealthy(self):
        servicer = HealthServicer()
        servicer.register_checker("test.Service", lambda: False)
        servicer.check_all()
        request = MagicMock(service="test.Service")
        response = servicer.Check(request, None)
        assert response.status == health_pb2.HealthCheckResponse.NOT_SERVING

    def test_checker_exception_marks_not_serving(self):
        servicer = HealthServicer()
        servicer.register_checker("test.Service", lambda: 1/0)
        servicer.check_all()
        request = MagicMock(service="test.Service")
        response = servicer.Check(request, None)
        assert response.status == health_pb2.HealthCheckResponse.NOT_SERVING

    def test_overall_status_unhealthy_if_any_service_unhealthy(self):
        servicer = HealthServicer()
        servicer.register_checker("healthy.Service", lambda: True)
        servicer.register_checker("unhealthy.Service", lambda: False)
        servicer.check_all()
        request = MagicMock(service="")
        response = servicer.Check(request, None)
        assert response.status == health_pb2.HealthCheckResponse.NOT_SERVING


class TestCreateHealthServicer:
    def test_with_transcription_service_available(self):
        mock_svc = MagicMock()
        mock_svc.model = MagicMock()  # Model is available
        
        servicer = create_health_servicer(transcription_svc=mock_svc)
        request = MagicMock(service="cognition.TranscriptionService")
        response = servicer.Check(request, None)
        assert response.status == health_pb2.HealthCheckResponse.SERVING

    def test_with_transcription_service_unavailable(self):
        mock_svc = MagicMock()
        mock_svc.model = None  # Model not loaded
        
        servicer = create_health_servicer(transcription_svc=mock_svc)
        request = MagicMock(service="cognition.TranscriptionService")
        response = servicer.Check(request, None)
        assert response.status == health_pb2.HealthCheckResponse.NOT_SERVING

    def test_with_llm_service_available(self):
        mock_svc = MagicMock()
        mock_svc.llm = MagicMock()
        
        servicer = create_health_servicer(llm_svc=mock_svc)
        request = MagicMock(service="cognition.LLMService")
        response = servicer.Check(request, None)
        assert response.status == health_pb2.HealthCheckResponse.SERVING

    def test_with_ocr_service_available(self):
        mock_svc = MagicMock()
        mock_svc.engine = MagicMock()
        
        servicer = create_health_servicer(ocr_svc=mock_svc)
        request = MagicMock(service="cognition.OCRService")
        response = servicer.Check(request, None)
        assert response.status == health_pb2.HealthCheckResponse.SERVING

    def test_with_vad_service_available(self):
        mock_svc = MagicMock()
        mock_svc.model = MagicMock()
        
        servicer = create_health_servicer(vad_svc=mock_svc)
        request = MagicMock(service="cognition.VADService")
        response = servicer.Check(request, None)
        assert response.status == health_pb2.HealthCheckResponse.SERVING

