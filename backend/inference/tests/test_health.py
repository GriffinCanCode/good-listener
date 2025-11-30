"""Tests for health check service."""

import time
from unittest.mock import MagicMock

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
        servicer.register_checker("test.Service", lambda: 1 / 0)
        servicer.check_all()
        request = MagicMock(service="test.Service")
        response = servicer.Check(request, None)
        assert response.status == health_pb2.HealthCheckResponse.NOT_SERVING

    def test_overall_status_unhealthy_if_required_service_unhealthy(self):
        servicer = HealthServicer()
        servicer.register_checker("healthy.Service", lambda: True, required=True)
        servicer.register_checker("unhealthy.Service", lambda: False, required=True)
        servicer.check_all()
        request = MagicMock(service="")
        response = servicer.Check(request, None)
        assert response.status == health_pb2.HealthCheckResponse.NOT_SERVING

    def test_overall_status_healthy_if_optional_service_unhealthy(self):
        servicer = HealthServicer()
        servicer.register_checker("healthy.Service", lambda: True, required=True)
        servicer.register_checker("optional.Service", lambda: False, required=False)
        servicer.check_all()
        request = MagicMock(service="")
        response = servicer.Check(request, None)
        assert response.status == health_pb2.HealthCheckResponse.SERVING


class TestLiveEndpoint:
    def test_live_always_serving(self):
        """Live endpoint returns SERVING regardless of model state."""
        servicer = HealthServicer()
        servicer.register_checker("test.Service", lambda: False, required=True)
        request = MagicMock(service="live")
        response = servicer.Check(request, None)
        assert response.status == health_pb2.HealthCheckResponse.SERVING

    def test_live_with_no_checkers(self):
        """Live endpoint works without any registered checkers."""
        servicer = HealthServicer()
        request = MagicMock(service="live")
        response = servicer.Check(request, None)
        assert response.status == health_pb2.HealthCheckResponse.SERVING


class TestReadyEndpoint:
    def test_ready_returns_serving_when_all_models_available(self):
        servicer = HealthServicer()
        servicer.register_checker("svc1", lambda: True, required=True)
        servicer.register_checker("svc2", lambda: True, required=False)
        request = MagicMock(service="ready")
        response = servicer.Check(request, None)
        assert response.status == health_pb2.HealthCheckResponse.SERVING

    def test_ready_returns_not_serving_when_required_model_unavailable(self):
        servicer = HealthServicer()
        servicer.register_checker("required", lambda: False, required=True)
        servicer.register_checker("optional", lambda: True, required=False)
        request = MagicMock(service="ready")
        response = servicer.Check(request, None)
        assert response.status == health_pb2.HealthCheckResponse.NOT_SERVING

    def test_ready_returns_not_serving_when_optional_model_unavailable(self):
        """Ready includes ALL services, even optional ones."""
        servicer = HealthServicer()
        servicer.register_checker("required", lambda: True, required=True)
        servicer.register_checker("optional", lambda: False, required=False)
        request = MagicMock(service="ready")
        response = servicer.Check(request, None)
        assert response.status == health_pb2.HealthCheckResponse.NOT_SERVING

    def test_ready_caches_result_with_ttl(self):
        call_count = 0
        def counter():
            nonlocal call_count
            call_count += 1
            return True

        servicer = HealthServicer(ready_ttl=60.0)
        servicer.register_checker("svc", counter, required=True)

        request = MagicMock(service="ready")
        servicer.Check(request, None)
        servicer.Check(request, None)
        servicer.Check(request, None)
        assert call_count == 1  # Only called once due to caching

    def test_ready_cache_expires_after_ttl(self):
        call_count = 0
        def counter():
            nonlocal call_count
            call_count += 1
            return True

        servicer = HealthServicer(ready_ttl=0.1)
        servicer.register_checker("svc", counter, required=True)

        request = MagicMock(service="ready")
        servicer.Check(request, None)
        time.sleep(0.15)  # Exceed TTL
        servicer.Check(request, None)
        assert call_count == 2  # Called twice after cache expired

    def test_ready_cache_invalidation(self):
        call_count = 0
        def counter():
            nonlocal call_count
            call_count += 1
            return True

        servicer = HealthServicer(ready_ttl=60.0)
        servicer.register_checker("svc", counter, required=True)

        request = MagicMock(service="ready")
        servicer.Check(request, None)
        servicer.invalidate_ready_cache()
        servicer.Check(request, None)
        assert call_count == 2  # Called again after invalidation

    def test_ready_with_no_checkers_returns_serving(self):
        """Ready with no checkers assumes healthy."""
        servicer = HealthServicer()
        request = MagicMock(service="ready")
        response = servicer.Check(request, None)
        assert response.status == health_pb2.HealthCheckResponse.SERVING

    def test_ready_exception_marks_not_serving(self):
        servicer = HealthServicer()
        servicer.register_checker("broken", lambda: 1 / 0, required=True)
        request = MagicMock(service="ready")
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

    def test_overall_healthy_with_llm_unavailable(self):
        """LLM service is optional, overall health should pass without it."""
        mock_transcription = MagicMock()
        mock_transcription.model = MagicMock()
        mock_vad = MagicMock()
        mock_vad.model = MagicMock()
        mock_ocr = MagicMock()
        mock_ocr.engine = MagicMock()
        mock_llm = MagicMock()
        mock_llm.llm = None  # LLM not available

        servicer = create_health_servicer(
            transcription_svc=mock_transcription,
            vad_svc=mock_vad,
            ocr_svc=mock_ocr,
            llm_svc=mock_llm,
        )
        request = MagicMock(service="")
        response = servicer.Check(request, None)
        assert response.status == health_pb2.HealthCheckResponse.SERVING
