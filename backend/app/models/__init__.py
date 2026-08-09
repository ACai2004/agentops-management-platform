"""导入所有模型，使它们注册到 Base.metadata（供 Alembic autogenerate 使用）。"""

from app.models.agent import Agent, AgentVersion
from app.models.capability import Capability
from app.models.datasource import Datasource
from app.models.feedback import Feedback
from app.models.knowledge import Knowledge
from app.models.plan import ModificationPlan
from app.models.publish import PublishRecord
from app.models.trace import Trace

__all__ = [
    "Agent",
    "AgentVersion",
    "Capability",
    "Datasource",
    "Feedback",
    "Knowledge",
    "ModificationPlan",
    "PublishRecord",
    "Trace",
]
