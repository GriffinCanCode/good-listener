"""gRPC health check service with model availability checks."""

import asyncio
from collections.abc import Callable

from grpc_health.v1 import health_pb2, health_pb2_grpc

from app.core import get_logger

logger = get_logger(__name__)
_RESP = health_pb2.HealthCheckResponse


class HealthServicer(health_pb2_grpc.HealthServicer):
    """Health servicer that checks model availability."""

    def __init__(self):
        self._status: dict[str, _RESP.ServingStatus] = {"": _RESP.SERVING}
        self._checkers: dict[str, Callable[[], bool]] = {}

    def register_checker(self, service: str, checker: Callable[[], bool]):
        """Register a health checker for a service."""
        self._checkers[service] = checker
        self._status[service] = _RESP.UNKNOWN

    def check_all(self):
        """Run all registered health checks and update statuses."""
        all_healthy = True
        for service, checker in self._checkers.items():
            try:
                healthy = checker()
                self._status[service] = _RESP.SERVING if healthy else _RESP.NOT_SERVING
                if not healthy:
                    all_healthy = False
                    logger.warning(f"health_check_failed service={service}")
            except Exception:
                self._status[service], all_healthy = _RESP.NOT_SERVING, False
                logger.exception("health_check_error service=%s", service)
        self._status[""] = _RESP.SERVING if all_healthy else _RESP.NOT_SERVING

    def Check(self, request, _context):
        status = self._status.get(request.service, _RESP.SERVICE_UNKNOWN)
        return _RESP(status=status)

    async def Watch(self, request, context):
        service, last_status = request.service, None
        while context.is_active():
            self.check_all()
            if (current := self._status.get(service, _RESP.SERVICE_UNKNOWN)) != last_status:
                yield _RESP(status=current)
                last_status = current
            await asyncio.sleep(5)


def create_health_servicer(transcription_svc=None, vad_svc=None, ocr_svc=None, llm_svc=None) -> HealthServicer:
    """Create health servicer with model checkers."""
    servicer = HealthServicer()
    checks = [
        (transcription_svc, "cognition.TranscriptionService", "model"),
        (vad_svc, "cognition.VADService", "model"),
        (ocr_svc, "cognition.OCRService", "engine"),
        (llm_svc, "cognition.LLMService", "llm"),
    ]
    for svc, name, attr in checks:
        if svc:
            servicer.register_checker(name, lambda s=svc, a=attr: getattr(s, a) is not None)
    servicer.check_all()
    return servicer
