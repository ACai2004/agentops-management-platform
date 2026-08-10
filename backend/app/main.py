from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import (
    agents,
    capabilities,
    feedback,
    optimization,
    publish,
    runs,
    versions,
)
from app.api import (
    datasource as datasource_api,
)
from app.api import (
    knowledge as knowledge_api,
)
from app.core.config import settings
from app.runtime.runner import StepLimitExceededError
from app.services.optimization_service import OptimizationError
from app.services.publish_service import PublishError

app = FastAPI(title="AgentOps API", version="0.1.0")

# CORS：MVP 仅开放给前端控制台（Layer 8）
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册全部路由（§11）
for _router in [
    agents.router,
    versions.router,
    runs.router,
    feedback.router,
    optimization.router,
    publish.router,
    capabilities.router,
    knowledge_api.router,
    datasource_api.router,
]:
    app.include_router(_router)


# ---- 异常 → HTTP 状态码（§11：400 校验失败 / 404 不存在 / 409 状态机冲突）----
@app.exception_handler(KeyError)
async def not_found_handler(request, exc: KeyError):
    return JSONResponse(status_code=404, content={"message": str(exc)})


@app.exception_handler(ValueError)
async def bad_request_handler(request, exc: ValueError):
    return JSONResponse(status_code=400, content={"message": str(exc)})


@app.exception_handler(PublishError)
async def publish_conflict_handler(request, exc: PublishError):
    return JSONResponse(status_code=409, content={"message": str(exc)})


@app.exception_handler(OptimizationError)
async def optimization_conflict_handler(request, exc: OptimizationError):
    return JSONResponse(status_code=409, content={"message": str(exc)})


@app.exception_handler(StepLimitExceededError)
async def step_limit_handler(request, exc: StepLimitExceededError):
    return JSONResponse(status_code=400, content={"message": str(exc)})


@app.get("/health")
def health() -> dict:
    """健康检查：服务存活即返回 ok。"""
    return {"status": "ok"}
