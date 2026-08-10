import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, Uuid, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class Agent(Base):
    __tablename__ = "agents"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str | None] = mapped_column(String, nullable=True)
    # 到 agent_versions 的循环外键：首次发布前为 null；use_alter 让建表时后置该约束
    current_version_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("agent_versions.id", use_alter=True, name="fk_agents_current_version_id"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    # 软删除：非空即已删除（历史数据保留，仅列表隐藏）
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AgentVersion(Base):
    __tablename__ = "agent_versions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    agent_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("agents.id"), nullable=False)
    version_no: Mapped[int] = mapped_column(Integer, nullable=False)  # 每个 Agent 内自增 1,2,3...
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    workflow_config: Mapped[dict] = mapped_column(JSONB, nullable=False)  # 符合 WorkflowConfig schema
    capability_bindings: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    knowledge_bindings: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)  # 绑定的知识名（实时引用）
    model_settings: Mapped[dict] = mapped_column(JSONB, nullable=False)  # 符合 ModelSettings
    status: Mapped[str] = mapped_column(String, nullable=False)  # "draft" | "published" | "rolled_back"
    created_by: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
