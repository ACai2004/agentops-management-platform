"""Layer 4 验收：创建 Agent → 建 draft → 发布 → current 切换 → 回滚 → 状态机约束生效。"""

import pytest
from sqlalchemy.orm import Session

from app.models.agent import Agent
from app.services import agent_service, publish_service
from app.services.publish_service import PublishError


def _count_published(db: Session, agent_id: int) -> int:
    return sum(
        1
        for v in agent_service.list_versions(db, agent_id)
        if v.status == agent_service.VERSION_STATUS_PUBLISHED
    )


def test_publish_lifecycle(db_session):
    agent = agent_service.create_agent(db_session, name="餐后体验回访助手", created_by="tester")
    assert agent.current_version_id is None

    # 初始 V1 draft
    versions = agent_service.list_versions(db_session, agent.id)
    assert len(versions) == 1
    v1 = versions[0]
    assert v1.version_no == 1
    assert v1.status == agent_service.VERSION_STATUS_DRAFT

    # 更新草稿
    v1 = agent_service.update_draft(db_session, v1.id, prompt="你是餐后体验回访助手。")
    assert v1.prompt == "你是餐后体验回访助手。"

    # 发布 V1 -> published + current
    v1 = publish_service.publish(db_session, v1.id, approved_by="tester")
    assert v1.status == agent_service.VERSION_STATUS_PUBLISHED
    assert db_session.get(Agent, agent.id).current_version_id == v1.id
    assert _count_published(db_session, agent.id) == 1

    # 建草稿 V2（复制 V1 内容）
    v2 = agent_service.create_draft(db_session, agent.id, created_by="tester")
    assert v2.version_no == 2
    assert v2.status == agent_service.VERSION_STATUS_DRAFT
    assert v2.prompt == v1.prompt

    # 发布 V2 -> current 切换，V1 变 rolled_back
    v2 = publish_service.publish(db_session, v2.id, approved_by="tester")
    assert v2.status == agent_service.VERSION_STATUS_PUBLISHED
    assert db_session.get(Agent, agent.id).current_version_id == v2.id
    assert agent_service.get_version(db_session, v1.id).status == agent_service.VERSION_STATUS_ROLLED_BACK
    assert _count_published(db_session, agent.id) == 1

    # 回滚到 V1 -> V1 重新 published 为 current，V2 变 rolled_back
    v1 = publish_service.rollback(db_session, agent.id, v1.id, approved_by="tester")
    assert v1.status == agent_service.VERSION_STATUS_PUBLISHED
    assert db_session.get(Agent, agent.id).current_version_id == v1.id
    assert agent_service.get_version(db_session, v2.id).status == agent_service.VERSION_STATUS_ROLLED_BACK
    assert _count_published(db_session, agent.id) == 1


def test_state_machine_constraints(db_session):
    agent = agent_service.create_agent(db_session, name="回访助手", created_by="tester")
    v1 = agent_service.list_versions(db_session, agent.id)[0]

    # draft 才能发布：已发布版本不能再次发布
    publish_service.publish(db_session, v1.id, approved_by="tester")
    with pytest.raises(PublishError):
        publish_service.publish(db_session, v1.id, approved_by="tester")

    # 新草稿可发布；随后旧版 rolled_back、新版 published，二者都不能再发布
    v2 = agent_service.create_draft(db_session, agent.id, created_by="tester")
    publish_service.publish(db_session, v2.id, approved_by="tester")
    with pytest.raises(PublishError):
        publish_service.publish(db_session, v1.id, approved_by="tester")
    with pytest.raises(PublishError):
        publish_service.publish(db_session, v2.id, approved_by="tester")

    # 回滚目标不能是 draft
    v3 = agent_service.create_draft(db_session, agent.id, created_by="tester")
    with pytest.raises(PublishError):
        publish_service.rollback(db_session, agent.id, v3.id, approved_by="tester")

    # 同一时间只有一个 published
    assert _count_published(db_session, agent.id) == 1


def test_update_draft_requires_draft_state(db_session):
    agent = agent_service.create_agent(db_session, name="回访助手", created_by="tester")
    v1 = agent_service.list_versions(db_session, agent.id)[0]
    publish_service.publish(db_session, v1.id, approved_by="tester")
    with pytest.raises(ValueError):
        agent_service.update_draft(db_session, v1.id, prompt="不允许改已发布版本")


def test_create_draft_when_no_published_yet(db_session):
    """current_version_id 为 null 时，create_draft 复制最新版本（V1）。"""
    agent = agent_service.create_agent(db_session, name="回访助手", created_by="tester")
    v1 = agent_service.list_versions(db_session, agent.id)[0]
    v2 = agent_service.create_draft(db_session, agent.id, created_by="tester")
    assert v2.version_no == 2
    assert v2.prompt == v1.prompt
    assert v2.status == agent_service.VERSION_STATUS_DRAFT
