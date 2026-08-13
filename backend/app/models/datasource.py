import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, Text, Uuid, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class Datasource(Base):
    __tablename__ = "datasources"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    base_url: Mapped[str] = mapped_column(Text, nullable=False)  # API 基础 URL
    method: Mapped[str] = mapped_column(String, nullable=False, default="GET")
    headers: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)  # 含 API key 等敏感配置
    param_defs: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)  # 参数契约 list[DatasourceParam]
    kind: Mapped[str | None] = mapped_column(String, nullable=True)  # weather / ocr / vision 等
    created_by: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
