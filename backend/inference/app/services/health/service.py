"""gRPC health check service - reports SERVING immediately for fast startup."""

import asyncio

from grpc_health.v1 import health_pb2, health_pb2_grpc

from app.core import get_logger

logger = get_logger(__name__)
_RESP = health_pb2.HealthCheckResponse


class HealthServicer(health_pb2_grpc.HealthServicer):
    """Health servicer that reports SERVING immediately. Models lazy-load on first use."""

    def __init__(self):
        self._status: dict[str, _RESP.ServingStatus] = {"": _RESP.SERVING}

    def Check(self, request, _context):
        return _RESP(status=self._status.get(request.service, _RESP.SERVING))

    async def Watch(self, request, context):
        service, last_status = request.service, None
        while context.is_active():
            if (current := self._status.get(service, _RESP.SERVING)) != last_status:
                yield _RESP(status=current)
                last_status = current
            await asyncio.sleep(5)


def create_health_servicer(**_) -> HealthServicer:
    """Create health servicer that reports SERVING immediately."""
    return HealthServicer()
