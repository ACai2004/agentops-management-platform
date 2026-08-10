"""AgentService：创建 Agent / 版本 CRUD / 草稿复制 / 软删除（§10.1）。

状态用字符串常量定义在此（§7 约定：不引第三方枚举库）。
"""

from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.contracts import AgentConfig, ModelSettings
from app.core.workflow_validation import validate_workflow
from app.models.agent import Agent, AgentVersion
from app.services.resources import resource_sets

VERSION_STATUS_DRAFT = "draft"
VERSION_STATUS_PUBLISHED = "published"
VERSION_STATUS_ROLLED_BACK = "rolled_back"

# 最小 workflow：单个 end 节点（create_agent 的初始草稿）
_MINIMAL_WORKFLOW = {"start": "end", "steps": {"end": {"type": "end"}}}


def create_agent(
    db: Session,
    *,
    name: str,
    description: str | None = None,
    created_by: str = "admin",
) -> Agent:
    """建 Agent，自动建 version_no=1 的 draft（空 prompt + 最小 workflow + 默认 model_settings）。"""
    agent = Agent(name=name, description=description)
    db.add(agent)
    db.flush()  # 获取 agent.id

    db.add(
        AgentVersion(
            agent_id=agent.id,
            version_no=1,
            prompt="",
            workflow_config=_MINIMAL_WORKFLOW,
            capability_bindings={},
            model_settings=ModelSettings().model_dump(),
            status=VERSION_STATUS_DRAFT,
            created_by=created_by,
        )
    )
    db.commit()
    db.refresh(agent)
    return agent


def list_agents(db: Session) -> list[Agent]:
    """未删除的 Agent 列表（软删除过滤）。"""
    return list(
        db.scalars(select(Agent).where(Agent.deleted_at.is_(None)).order_by(Agent.created_at.desc()))
    )


def get_agent(db: Session, agent_id) -> Agent | None:
    """获取未删除的 Agent。"""
    return db.scalar(select(Agent).where(Agent.id == agent_id, Agent.deleted_at.is_(None)))


def delete_agent(db: Session, agent_id) -> None:
    """软删除：标记 deleted_at，历史数据（版本/记录/反馈）保留。"""
    agent = get_agent(db, agent_id)
    if not agent:
        raise KeyError(f"Agent {agent_id} 不存在或已删除")
    agent.deleted_at = datetime.now(UTC)
    db.commit()


def create_draft(db: Session, agent_id, *, created_by: str = "admin") -> AgentVersion:
    """复制当前版本为新 draft（version_no+1），status=draft。

    源版本取 current_version_id；尚未发布过（current 为 null）时取最新版本。
    """
    agent = db.get(Agent, agent_id)
    if not agent:
        raise KeyError(f"Agent {agent_id} 不存在")

    source = db.get(AgentVersion, agent.current_version_id) if agent.current_version_id else None
    if not source:
        source = db.scalar(
            select(AgentVersion)
            .where(AgentVersion.agent_id == agent_id)
            .order_by(AgentVersion.version_no.desc())
            .limit(1)
        )
    if not source:
        raise KeyError(f"Agent {agent_id} 没有可复制的版本")

    next_no = (
        db.scalar(select(func.max(AgentVersion.version_no)).where(AgentVersion.agent_id == agent_id)) or 0
    ) + 1

    draft = AgentVersion(
        agent_id=agent_id,
        version_no=next_no,
        prompt=source.prompt,
        workflow_config=source.workflow_config,
        capability_bindings=source.capability_bindings,
        model_settings=source.model_settings,
        status=VERSION_STATUS_DRAFT,
        created_by=created_by,
    )
    db.add(draft)
    db.commit()
    db.refresh(draft)
    return draft


def get_version(db: Session, version_id) -> AgentVersion | None:
    return db.get(AgentVersion, version_id)


def list_versions(db: Session, agent_id) -> list[AgentVersion]:
    return list(
        db.scalars(
            select(AgentVersion)
            .where(AgentVersion.agent_id == agent_id)
            .order_by(AgentVersion.version_no)
        )
    )


def update_draft(
    db: Session,
    version_id,
    *,
    prompt=None,
    workflow_config=None,
    capability_bindings=None,
    model_settings=None,
) -> AgentVersion:
    """更新草稿（仅 draft 可编辑），改后整体按 AgentConfig 校验（§10.1）。"""
    version = db.get(AgentVersion, version_id)
    if not version:
        raise KeyError(f"版本 {version_id} 不存在")
    if version.status != VERSION_STATUS_DRAFT:
        raise ValueError(f"只有 draft 版本可编辑，当前状态={version.status}")

    if prompt is not None:
        version.prompt = prompt
    if workflow_config is not None:
        version.workflow_config = workflow_config
    if capability_bindings is not None:
        version.capability_bindings = capability_bindings
    if model_settings is not None:
        version.model_settings = model_settings

    # 整体校验为合法 AgentConfig，非法则抛错、不落库
    try:
        config = AgentConfig.model_validate(
            {
                "prompt": version.prompt,
                "workflow": version.workflow_config,
                "capability_bindings": version.capability_bindings,
                "knowledge_bindings": version.knowledge_bindings,
                "model_settings": version.model_settings,
            }
        )
    except Exception as e:
        raise ValueError(f"版本配置校验失败：{e}") from e

    # 拓扑 + 语义校验（含资源存在性）：error 拒绝保存（warning 放行，编辑中可暂存）
    ds, kn = resource_sets(db)
    errors = [
        i for i in validate_workflow(config, existing_datasources=ds, existing_knowledge=kn)
        if i.severity == "error"
    ]
    if errors:
        raise ValueError(f"Workflow 校验未通过：{errors[0].message}")

    db.commit()
    db.refresh(version)
    return version
