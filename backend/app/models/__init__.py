"""导入所有模型，使它们注册到 Base.metadata（供 Alembic autogenerate 使用）。"""

from app.models.agent import Agent, AgentVersion
from app.models.capability import Capability
from app.models.feedback import Feedback
from app.models.plan import ModificationPlan
from app.models.publish import PublishRecord
from app.models.trace import Trace

__all__ = [
    "Agent",
    "AgentVersion",
    "Capability",
    "Feedback",
    "ModificationPlan",
    "PublishRecord",
    "Trace",
]
