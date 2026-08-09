from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings

app = FastAPI(title="AgentOps API", version="0.1.0")

# CORS：MVP 仅开放给前端控制台（Layer 8）
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict:
    """健康检查：服务存活即返回 ok。"""
    return {"status": "ok"}
