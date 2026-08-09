import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, Text, Uuid, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class Capability(Base):
    __tablename__ = "capabilities"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    trigger: Mapped[str | None] = mapped_column(String, nullable=True)  # 适用场景
    behavior_instruction: Mapped[str] = mapped_column(Text, nullable=False)  # 行为指令（作为节点 prompt 片段）
    output_spec: Mapped[str | None] = mapped_column(Text, nullable=True)  # 输出约定
    examples: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)  # list[str]
    created_by: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
