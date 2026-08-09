"""CapabilityService：能力库 CRUD / 绑定 / 沉淀（§10.5）。

MVP 中 Capability 不参与运行时逻辑（无工具调用），只是"可复用的行为片段库"。
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.agent import AgentVersion
from app.models.capability import Capability
from app.services.agent_service import VERSION_STATUS_DRAFT


def create_capability(
    db: Session,
    *,
    name: str,
    description: str,
    trigger: str | None = None,
    behavior_instruction: str,
    output_spec: str | None = None,
    examples: list | None = None,
    created_by: str = "admin",
) -> Capability:
    cap = Capability(
        name=name,
        description=description,
        trigger=trigger,
        behavior_instruction=behavior_instruction,
        output_spec=output_spec,
        examples=examples or [],
        created_by=created_by,
    )
    db.add(cap)
    db.commit()
    db.refresh(cap)
    return cap


def list_capabilities(db: Session) -> list[Capability]:
    return list(db.scalars(select(Capability).order_by(Capability.name)))


def get_capability(db: Session, name: str) -> Capability | None:
    return db.scalar(select(Capability).where(Capability.name == name))


def bind_capability(
    db: Session, version_id, capability_name: str, params: dict | None = None
) -> AgentVersion:
    """写入 draft 的 capability_bindings（仅 draft 可改）。"""
    version = db.get(AgentVersion, version_id)
    if not version:
        raise KeyError(f"版本 {version_id} 不存在")
    if version.status != VERSION_STATUS_DRAFT:
        raise ValueError("只有 draft 版本可绑定能力")
    if not get_capability(db, capability_name):
        raise KeyError(f"能力 {capability_name} 不存在")
    bindings = dict(version.capability_bindings or {})
    bindings[capability_name] = params or {}
    version.capability_bindings = bindings
    db.commit()
    db.refresh(version)
    return version


def save_as_capability(
    db: Session,
    version_id,
    node_id: str,
    *,
    name: str,
    description: str | None = None,
    created_by: str = "admin",
) -> Capability:
    """把 workflow 中某 llm 节点的 prompt 沉淀为一个 Capability（名字可由业务人员起名）。"""
    version = db.get(AgentVersion, version_id)
    if not version:
        raise KeyError(f"版本 {version_id} 不存在")
    node = (version.workflow_config or {}).get("steps", {}).get(node_id)
    if not node:
        raise KeyError(f"节点 {node_id} 不存在")
    if node.get("type") != "llm":
        raise ValueError("只能把 llm 节点沉淀为能力")
    return create_capability(
        db,
        name=name,
        description=description or f"从节点 {node_id} 沉淀",
        behavior_instruction=node.get("prompt") or "",
        created_by=created_by,
    )
