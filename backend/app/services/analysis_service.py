"""AnalysisService：Trace 查询 / 反馈标注（§10.3）。"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.feedback import Feedback
from app.models.trace import Trace


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
