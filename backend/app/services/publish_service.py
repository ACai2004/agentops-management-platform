"""PublishService：发布/回滚状态机 + PublishRecord（§10.2）。

状态机约束：draft 才能发布；同一时间只有一个 published。
"""

from sqlalchemy.orm import Session

from app.core.contracts import AgentConfig
from app.core.workflow_validation import validate_workflow
from app.models.agent import Agent, AgentVersion
from app.models.publish import PublishRecord
from app.services.agent_service import (
    VERSION_STATUS_DRAFT,
    VERSION_STATUS_PUBLISHED,
    VERSION_STATUS_ROLLED_BACK,
)
from app.services.resources import resource_sets


class PublishError(Exception):
    """发布/回滚的状态机约束冲突。"""


def _set_current(db: Session, agent: Agent, version: AgentVersion, action: str, approved_by: str) -> None:
    """把 version 置为当前发布版本：旧 current 标记 rolled_back，写 PublishRecord。"""
    if agent.current_version_id and agent.current_version_id != version.id:
        old = db.get(AgentVersion, agent.current_version_id)
        if old is not None:
            old.status = VERSION_STATUS_ROLLED_BACK
    version.status = VERSION_STATUS_PUBLISHED
    agent.current_version_id = version.id
    db.add(
        PublishRecord(
            version_id=version.id,
            agent_id=agent.id,
            action=action,
            release_ratio=100.0,  # 本地无灰度，恒为 100%
            approved_by=approved_by,
        )
    )
    db.commit()


def publish(db: Session, version_id, *, approved_by: str = "admin") -> AgentVersion:
    """发布：只有 draft 版本可发布，置为 published 并成为 current。"""
    version = db.get(AgentVersion, version_id)
    if not version:
        raise PublishError(f"版本 {version_id} 不存在")
    if version.status != VERSION_STATUS_DRAFT:
        raise PublishError(f"只有 draft 版本可发布，当前状态={version.status}")
    agent = db.get(Agent, version.agent_id)
    if not agent:
        raise PublishError("所属 Agent 不存在")

    # 发布前校验：error + warning 都拒绝（要上线的图必须干净，§10.2）
    config = AgentConfig.model_validate(
        {
            "prompt": version.prompt,
            "workflow": version.workflow_config,
            "capability_bindings": version.capability_bindings,
            "knowledge_bindings": version.knowledge_bindings,
            "model_settings": version.model_settings,
        }
    )
    ds, kn = resource_sets(db)
    issues = validate_workflow(config, existing_datasources=ds, existing_knowledge=kn)
    if issues:
        raise PublishError(f"发布前校验未通过：{issues[0].message}（{issues[0].code}）")

    _set_current(db, agent, version, "publish", approved_by)
    db.refresh(version)
    return version


def rollback(db: Session, agent_id, target_version_id, *, approved_by: str = "admin") -> AgentVersion:
    """回滚：目标必须是历史 published/rolled_back 版本，重新设为 current，原 current 置 rolled_back。"""
    agent = db.get(Agent, agent_id)
    if not agent:
        raise PublishError(f"Agent {agent_id} 不存在")
    target = db.get(AgentVersion, target_version_id)
    if not target or target.agent_id != agent_id:
        raise PublishError("目标版本不存在或不属于该 Agent")
    if target.status == VERSION_STATUS_DRAFT:
        raise PublishError("draft 版本不能作为回滚目标")
    _set_current(db, agent, target, "rollback", approved_by)
    db.refresh(target)
    return target
