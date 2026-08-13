"""Agent 元数据（重命名 / 描述 / 软删除）测试。"""

import pytest

from app.services import agent_service


def test_update_agent_rename(db_session):
    agent = agent_service.create_agent(db_session, name="旧名字", created_by="tester")
    updated = agent_service.update_agent(db_session, agent.id, name="新名字")
    assert updated.name == "新名字"
    assert agent_service.get_agent(db_session, agent.id).name == "新名字"


def test_update_agent_empty_name_rejected(db_session):
    agent = agent_service.create_agent(db_session, name="旧名字", created_by="tester")
    with pytest.raises(ValueError):
        agent_service.update_agent(db_session, agent.id, name="   ")


def test_update_agent_soft_deleted_not_found(db_session):
    agent = agent_service.create_agent(db_session, name="x", created_by="tester")
    agent_service.delete_agent(db_session, agent.id)
    with pytest.raises(KeyError):
        agent_service.update_agent(db_session, agent.id, name="y")


def test_update_draft_saves_broken_workflow(db_session):
    """保存不拦逻辑问题：缺 end / 悬空边等都能存，问题留到运行/发布时提示。"""
    agent = agent_service.create_agent(db_session, name="x", created_by="tester")
    v1 = agent_service.list_versions(db_session, agent.id)[0]
    broken = {"start": "a", "steps": {"a": {"type": "llm", "prompt": "x", "save_as": "y", "next": "ghost"}}}
    v1 = agent_service.update_draft(db_session, v1.id, prompt="p", workflow_config=broken)
    assert v1.workflow_config == broken
    assert v1.status == "draft"
