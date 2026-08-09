"""KnowledgeService：知识库 CRUD / 绑定（§10.6）。

语义：知识实时引用——content 变更立即对绑定 Agent 生效，无需重新发布。
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.agent import AgentVersion
from app.models.knowledge import Knowledge
from app.services.agent_service import VERSION_STATUS_DRAFT


def create_knowledge(
    db: Session,
    *,
    name: str,
    kind: str,
    content: str,
    created_by: str = "admin",
) -> Knowledge:
    k = Knowledge(name=name, kind=kind, content=content, created_by=created_by)
    db.add(k)
    db.commit()
    db.refresh(k)
    return k


def list_knowledges(db: Session) -> list[Knowledge]:
    return list(db.scalars(select(Knowledge).order_by(Knowledge.name)))


def get_knowledge(db: Session, name: str) -> Knowledge | None:
    return db.scalar(select(Knowledge).where(Knowledge.name == name))


def update_knowledge(db: Session, name: str, *, content: str) -> Knowledge:
    k = get_knowledge(db, name)
    if not k:
        raise KeyError(f"知识 {name} 不存在")
    k.content = content
    db.commit()
    db.refresh(k)
    return k


def bind_knowledge(db: Session, version_id, knowledge_name: str) -> AgentVersion:
    """写入 draft 的 knowledge_bindings（仅 draft 可改）。"""
    version = db.get(AgentVersion, version_id)
    if not version:
        raise KeyError(f"版本 {version_id} 不存在")
    if version.status != VERSION_STATUS_DRAFT:
        raise ValueError("只有 draft 版本可绑定知识")
    if not get_knowledge(db, knowledge_name):
        raise KeyError(f"知识 {knowledge_name} 不存在")
    if knowledge_name not in (version.knowledge_bindings or []):
        version.knowledge_bindings = [*(version.knowledge_bindings or []), knowledge_name]
    db.commit()
    db.refresh(version)
    return version


def unbind_knowledge(db: Session, version_id, knowledge_name: str) -> AgentVersion:
    version = db.get(AgentVersion, version_id)
    if not version:
        raise KeyError(f"版本 {version_id} 不存在")
    if version.status != VERSION_STATUS_DRAFT:
        raise ValueError("只有 draft 版本可解绑知识")
    version.knowledge_bindings = [n for n in (version.knowledge_bindings or []) if n != knowledge_name]
    db.commit()
    db.refresh(version)
    return version
