"""AnalysisService：Trace 查询 / 反馈标注 / 运行入库（§10.3）。"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.contracts import AgentConfig
from app.models.agent import AgentVersion
from app.models.feedback import Feedback
from app.models.trace import Trace
from app.runtime.runner import run_agent
from app.services import datasource_service, knowledge_service


async def run_version(db: Session, version: AgentVersion, user_input: str, env: str = "test", image_url: str | None = None) -> Trace:
    """运行一个 AgentVersion 并入库为 Trace（服务层从 DB 解析数据源/知识注入）。"""
    config = AgentConfig.model_validate(
        {
            "prompt": version.prompt,
            "workflow": version.workflow_config,
            "capability_bindings": version.capability_bindings,
            "knowledge_bindings": version.knowledge_bindings,
            "model_settings": version.model_settings,
        }
    )
    datasources = {
        d.name: {"base_url": d.base_url, "method": d.method, "headers": d.headers}
        for d in datasource_service.list_datasources(db)
    }
    knowledges = {k.name: k.content for k in knowledge_service.list_knowledges(db)}
    record = await run_agent(
        config, user_input, env,
        agent_id=str(version.agent_id), version_id=str(version.id),
        image_url=image_url, datasources=datasources, knowledges=knowledges,
    )
    trace = Trace(
        agent_id=version.agent_id,
        version_id=version.id,
        env=env,
        input=user_input,
        steps=[s.model_dump() for s in record.steps],
        output=record.output,
        model=record.model,
    )
    db.add(trace)
    db.commit()
    db.refresh(trace)
    return trace


def list_traces(
    db: Session, agent_id, env: str | None = None, limit: int = 50, offset: int = 0
) -> list[Trace]:
    q = select(Trace).where(Trace.agent_id == agent_id)
    if env:
        q = q.where(Trace.env == env)
    return list(db.scalars(q.order_by(Trace.created_at.desc()).limit(limit).offset(offset)))


def get_trace(db: Session, trace_id) -> Trace | None:
    return db.get(Trace, trace_id)


def add_feedback(db: Session, trace_id, text: str, created_by: str) -> Feedback:
    """创建 Feedback(status=open)。"""
    fb = Feedback(trace_id=trace_id, text=text, created_by=created_by, status="open")
    db.add(fb)
    db.commit()
    db.refresh(fb)
    return fb


def list_feedbacks(db: Session, agent_id) -> list[Feedback]:
    return list(
        db.scalars(
            select(Feedback)
            .join(Trace, Feedback.trace_id == Trace.id)
            .where(Trace.agent_id == agent_id)
            .order_by(Feedback.created_at.desc())
        )
    )
