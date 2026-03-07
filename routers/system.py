from fastapi import APIRouter
from starlette.responses import Response
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

system_router = APIRouter(tags=["System"])


@system_router.get("/metrics", include_in_schema=False)
async def metrics():
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


@system_router.get("/health", include_in_schema=False)
async def health_check():
    return {"status": "ok"}
