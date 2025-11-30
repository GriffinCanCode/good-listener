"""gRPC health check service with live/ready endpoints and TTL caching."""

import asyncio
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from threading import Lock

from grpc_health.v1 import health_pb2, health_pb2_grpc

from app.core import get_logger

logger = get_logger(__name__)
_RESP = health_pb2.HealthCheckResponse


@dataclass(slots=True)
class CachedResult:
    """Cached health check result with TTL."""
    healthy: bool
    checked_at: float
    ttl: float

    @property
    def is_valid(self) -> bool:
        return (time.monotonic() - self.checked_at) < self.ttl


@dataclass(slots=True)
class ServiceChecker:
    """Health checker for a specific service."""
    check_fn: Callable[[], bool]
    required: bool = False
    cached: CachedResult | None = field(default=None)


class HealthServicer(health_pb2_grpc.HealthServicer):
    """Health servicer supporting live (immediate) and ready (model validation with TTL) checks."""

    LIVE_SERVICE = "live"
    READY_SERVICE = "ready"
    DEFAULT_TTL = 30.0  # Cache readiness for 30s

    def __init__(self, ready_ttl: float = DEFAULT_TTL):
        self._status: dict[str, _RESP.ServingStatus] = {"": _RESP.SERVING}
        self._checkers: dict[str, ServiceChecker] = {}
        self._ready_ttl = ready_ttl
        self._ready_cache: CachedResult | None = None
        self._lock = Lock()

    def register_checker(self, service: str, check_fn: Callable[[], bool], required: bool = False) -> None:
        """Register a health checker for a service."""
        with self._lock:
            self._checkers[service] = ServiceChecker(check_fn=check_fn, required=required)
            self._status[service] = _RESP.UNKNOWN

    def check_all(self) -> None:
        """Run all registered checkers and update statuses."""
        with self._lock:
            any_required_failed = False
            for svc, checker in self._checkers.items():
                try:
                    healthy = checker.check_fn()
                    self._status[svc] = _RESP.SERVING if healthy else _RESP.NOT_SERVING
                    if checker.required and not healthy:
                        any_required_failed = True
                except Exception:
                    logger.exception(f"Health check failed for {svc}")
                    self._status[svc] = _RESP.NOT_SERVING
                    if checker.required:
                        any_required_failed = True
            # Update overall status based on required services
            self._status[""] = _RESP.NOT_SERVING if any_required_failed else _RESP.SERVING

    def _check_ready(self) -> _RESP.ServingStatus:
        """Check readiness with TTL caching. Validates all registered model checkers."""
        with self._lock:
            if self._ready_cache and self._ready_cache.is_valid:
                return _RESP.SERVING if self._ready_cache.healthy else _RESP.NOT_SERVING

            # Run all checkers for readiness
            all_healthy = True
            for svc, checker in self._checkers.items():
                try:
                    if not checker.check_fn():
                        all_healthy = False
                        if checker.required:
                            break  # Fast-fail on required service
                except Exception:
                    logger.exception(f"Readiness check failed for {svc}")
                    all_healthy = False
                    if checker.required:
                        break

            self._ready_cache = CachedResult(healthy=all_healthy, checked_at=time.monotonic(), ttl=self._ready_ttl)
            logger.debug("readiness_check", healthy=all_healthy, ttl=self._ready_ttl)
            return _RESP.SERVING if all_healthy else _RESP.NOT_SERVING

    def Check(self, request, _context):
        """Handle health check - routes live vs ready vs service-specific."""
        service = request.service

        # Live check: always SERVING if server is running
        if service == self.LIVE_SERVICE:
            return _RESP(status=_RESP.SERVING)

        # Ready check: validate models with TTL caching
        if service == self.READY_SERVICE:
            return _RESP(status=self._check_ready())

        # Service-specific or overall check
        with self._lock:
            if service in self._status:
                return _RESP(status=self._status[service])
            return _RESP(status=_RESP.SERVICE_UNKNOWN)

    async def Watch(self, request, context):
        """Stream health status changes."""
        service, last_status = request.service, None
        while context.is_active():
            # For ready service, use cached check
            if service == self.READY_SERVICE:
                current = self._check_ready()
            elif service == self.LIVE_SERVICE:
                current = _RESP.SERVING
            else:
                with self._lock:
                    current = self._status.get(service, _RESP.SERVICE_UNKNOWN)

            if current != last_status:
                yield _RESP(status=current)
                last_status = current
            await asyncio.sleep(5)

    def invalidate_ready_cache(self) -> None:
        """Invalidate the readiness cache, forcing next check to re-validate."""
        with self._lock:
            self._ready_cache = None


def create_health_servicer(
    transcription_svc=None,
    vad_svc=None,
    ocr_svc=None,
    llm_svc=None,
    ready_ttl: float = HealthServicer.DEFAULT_TTL,
) -> HealthServicer:
    """Create health servicer with model availability checkers."""
    servicer = HealthServicer(ready_ttl=ready_ttl)

    if transcription_svc:
        servicer.register_checker(
            "cognition.TranscriptionService",
            lambda svc=transcription_svc: svc.model is not None,
            required=True,
        )
    if vad_svc:
        servicer.register_checker(
            "cognition.VADService",
            lambda svc=vad_svc: svc.model is not None,
            required=True,
        )
    if ocr_svc:
        servicer.register_checker(
            "cognition.OCRService",
            lambda svc=ocr_svc: svc.engine is not None,
            required=True,
        )
    if llm_svc:
        servicer.register_checker(
            "cognition.LLMService",
            lambda svc=llm_svc: svc.llm is not None,
            required=False,  # LLM is optional
        )

    servicer.check_all()
    return servicer
