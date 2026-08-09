"""共享资源名集合（供校验的 DATASOURCE_MISSING / KNOWLEDGE_BINDING_MISSING 使用）。"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.datasource import Datasource
from app.models.knowledge import Knowledge


def resource_sets(db: Session) -> tuple[set[str], set[str]]:
    """返回 (数据源名集合, 知识名集合)。"""
    return (
        set(db.scalars(select(Datasource.name))),
        set(db.scalars(select(Knowledge.name))),
    )
