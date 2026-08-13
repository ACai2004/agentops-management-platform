"""运行 / Trace / 反馈路由（§11）。"""

from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api import dump
from app.core.db import get_db
from app.models.agent import Agent, AgentVersion
from app.models.trace import Trace
from app.services import analysis_service

router = APIRouter(prefix="/api", tags=["runs"])


class RunBody(BaseModel):
    input: str = ""                   # 兼容：单文本输入
    image_url: str | None = None      # 兼容：单图片输入
    inputs: dict | None = None        # 命名输入 {字段名: 值}（按工作流输入清单）
    version_id: UUID | None = None
    env: str = "test"


@router.post("/agents/{agent_id}/run")
async def run_agent_endpoint(agent_id: UUID, body: RunBody, db: Session = Depends(get_db)):
    agent = db.get(Agent, agent_id)
    if not agent:
        raise KeyError(f"Agent {agent_id} 不存在")
    version_id = body.version_id or agent.current_version_id
    if not version_id:
        raise KeyError("Agent 尚无当前版本")
    version = db.get(AgentVersion, version_id)
    trace = await analysis_service.run_version(
        db, version, body.input, body.env, image_url=body.image_url, inputs=body.inputs
    )
    return dump(trace)


@router.get("/traces")
def list_traces(
    agent_id: UUID | None = None,
    env: str | None = None,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    if not agent_id:
        return [
            dump(t)
            for t in db.scalars(select(Trace).order_by(Trace.created_at.desc()).limit(limit)).all()
        ]
    return [dump(t) for t in analysis_service.list_traces(db, agent_id, env=env, limit=limit)]


@router.get("/traces/{trace_id}")
def get_trace(trace_id: UUID, db: Session = Depends(get_db)):
    t = analysis_service.get_trace(db, trace_id)
    if not t:
        raise KeyError(f"Trace {trace_id} 不存在")
    return dump(t)


class FeedbackBody(BaseModel):
    text: str
    created_by: str = "admin"


@router.post("/traces/{trace_id}/feedback")
def add_feedback(trace_id: UUID, body: FeedbackBody, db: Session = Depends(get_db)):
    return dump(analysis_service.add_feedback(db, trace_id, body.text, body.created_by))
