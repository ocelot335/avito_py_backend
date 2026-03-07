import time
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from prometheus_client import Counter, Histogram

REQUEST_COUNT = Counter(
    "http_requests_total",
    "Общее количество HTTP запросов",
    ["method", "endpoint", "status"],
)

REQUEST_DURATION = Histogram(
    "http_request_duration_seconds",
    "Время обработки HTTP запроса",
    ["method", "endpoint"],
)


class PrometheusMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        method = request.method
        start_time = time.time()

        response = await call_next(request)

        duration = time.time() - start_time

        route = request.scope.get("route")
        endpoint = route.path if route else request.url.path

        REQUEST_COUNT.labels(
            method=method, endpoint=endpoint, status=response.status_code
        ).inc()

        REQUEST_DURATION.labels(method=method, endpoint=endpoint).observe(
            duration
        )

        return response
