"""AnalysisService：Trace 查询 / 反馈标注 / 运行入库（§10.3）。"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.contracts import AgentConfig
from app.models.agent import AgentVersion
from app.models.feedback import Feedback
from app.models.trace import Trace
from app.runtime.runner import run_agent
from app.services import datasource_service, knowledge_service


def _normalize_inputs(config: AgentConfig, inputs: dict | None, user_input: str, image_url: str | None) -> dict:
    """把命名 inputs 与兼容的平铺 input/image_url 合并为完整命名输入。

    按 workflow 的输入 schema 映射：有 text 字段时平铺 input 归入该字段，有 image 字段时
    平铺 image_url 归入该字段；无 schema（旧工作流）时保持 inputs 原样。
    """
    inputs = dict(inputs or {})
    schema = config.workflow.inputs
    text_field = next((f for f in schema if f.type != "image"), None)
    img_field = next((f for f in schema if f.type == "image"), None)
    if text_field and user_input and text_field.name not in inputs:
        inputs[text_field.name] = user_input
    if img_field and image_url and img_field.name not in inputs:
        inputs[img_field.name] = image_url
    return inputs


async def run_version(
    db: Session,
    version: AgentVersion,
    user_input: str = "",
    env: str = "test",
    image_url: str | None = None,
    inputs: dict | None = None,
) -> Trace:
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
        d.name: {"base_url": d.base_url, "method": d.method, "headers": d.headers, "param_defs": d.param_defs or []}
        for d in datasource_service.list_datasources(db)
    }
    knowledges = {k.name: k.content for k in knowledge_service.list_knowledges(db)}
    normalized = _normalize_inputs(config, inputs, user_input, image_url)
    record = await run_agent(
        config, user_input, env,
        agent_id=str(version.agent_id), version_id=str(version.id),
        image_url=image_url, datasources=datasources, knowledges=knowledges,
        inputs=normalized,
    )
    trace = Trace(
        agent_id=version.agent_id,
        version_id=version.id,
        env=env,
        input=record.input,
        inputs=record.inputs,
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
