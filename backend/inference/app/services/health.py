"""gRPC health check service with model availability checks."""

import asyncio
from typing import Callable

from grpc_health.v1 import health_pb2, health_pb2_grpc
from grpc_health.v1.health import HealthServicer as BaseHealthServicer

from app.core import get_logger

logger = get_logger(__name__)


class HealthServicer(health_pb2_grpc.HealthServicer):
    """Health servicer that checks model availability."""

    def __init__(self):
        self._status: dict[str, health_pb2.HealthCheckResponse.ServingStatus] = {}
        self._checkers: dict[str, Callable[[], bool]] = {}
        self._set_status("", health_pb2.HealthCheckResponse.SERVING)

    def _set_status(self, service: str, status: health_pb2.HealthCheckResponse.ServingStatus):
        self._status[service] = status

    def register_checker(self, service: str, checker: Callable[[], bool]):
        """Register a health checker for a service."""
        self._checkers[service] = checker
        self._set_status(service, health_pb2.HealthCheckResponse.UNKNOWN)

    def check_all(self):
        """Run all registered health checks and update statuses."""
        all_healthy = True
        for service, checker in self._checkers.items():
            try:
                healthy = checker()
                status = health_pb2.HealthCheckResponse.SERVING if healthy else health_pb2.HealthCheckResponse.NOT_SERVING
                self._set_status(service, status)
                if not healthy:
                    all_healthy = False
                    logger.warning(f"health_check_failed service={service}")
            except Exception as e:
                self._set_status(service, health_pb2.HealthCheckResponse.NOT_SERVING)
                all_healthy = False
                logger.error(f"health_check_error service={service} error={e}")
        
        self._set_status("", health_pb2.HealthCheckResponse.SERVING if all_healthy else health_pb2.HealthCheckResponse.NOT_SERVING)

    def Check(self, request, context):
        service = request.service
        if service in self._status:
            return health_pb2.HealthCheckResponse(status=self._status[service])
        return health_pb2.HealthCheckResponse(status=health_pb2.HealthCheckResponse.SERVICE_UNKNOWN)

    async def Watch(self, request, context):
        service = request.service
        last_status = None
        while context.is_active():
            self.check_all()
            current = self._status.get(service, health_pb2.HealthCheckResponse.SERVICE_UNKNOWN)
            if current != last_status:
                yield health_pb2.HealthCheckResponse(status=current)
                last_status = current
            await asyncio.sleep(5)


def create_health_servicer(
    transcription_svc=None,
    vad_svc=None,
    ocr_svc=None,
    llm_svc=None,
) -> HealthServicer:
    """Create health servicer with model checkers."""
    servicer = HealthServicer()

    if transcription_svc:
        servicer.register_checker(
            "cognition.TranscriptionService",
            lambda svc=transcription_svc: svc.model is not None,
        )

    if vad_svc:
        servicer.register_checker(
            "cognition.VADService",
            lambda svc=vad_svc: svc.model is not None,
        )

    if ocr_svc:
        servicer.register_checker(
            "cognition.OCRService",
            lambda svc=ocr_svc: svc.engine is not None,
        )

    if llm_svc:
        servicer.register_checker(
            "cognition.LLMService",
            lambda svc=llm_svc: svc.llm is not None,
        )

    servicer.check_all()
    return servicer

