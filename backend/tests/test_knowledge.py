"""Layer 6 验收：能力 / 知识库 / 数据源 + KNOWLEDGE_BINDING_MISSING / DATASOURCE_MISSING 校验生效。"""

import pytest

from app.core.contracts import AgentConfig, WorkflowConfig
from app.runtime import nodes
from app.runtime.runner import run_agent
from app.services import agent_service, capability_service, datasource_service, knowledge_service, publish_service
from app.services.publish_service import PublishError
from tests.sample_data import SAMPLE_WORKFLOW

# ---------- 验收：创建知识 → 绑定到草稿 → 运行时回复基于知识内容 ----------


@pytest.mark.asyncio
async def test_knowledge_create_bind_inject(monkeypatch, db_session):
    knowledge_service.create_knowledge(
        db_session, name="餐厅菜单", kind="menu", content="招牌：麻辣香锅 58元（多人分享）"
    )
    agent = agent_service.create_agent(db_session, name="推荐助手", created_by="tester")
    v1 = agent_service.list_versions(db_session, agent.id)[0]
    v1 = knowledge_service.bind_knowledge(db_session, v1.id, "餐厅菜单")
    assert v1.knowledge_bindings == ["餐厅菜单"]

    captured = {}

    async def fake_call(messages, model="primary", temperature=0.7, max_tokens=1024, json_mode=False):
        captured["messages"] = messages
        return "推荐麻辣香锅"

    monkeypatch.setattr(nodes, "call", fake_call)

    cfg = AgentConfig(
        prompt="你是推荐助手",
        workflow=WorkflowConfig.model_validate(SAMPLE_WORKFLOW),
        knowledge_bindings=["餐厅菜单"],
    )
    await run_agent(cfg, "推荐一道菜", env="test", knowledges={"餐厅菜单": "招牌：麻辣香锅 58元（多人分享）"})
    system = captured["messages"][0]["content"]
    assert "麻辣香锅" in system  # 知识内容注入系统消息
    assert "餐厅菜单" in system


# ---------- 验收：创建数据源（高德天气）→ http 节点引用 ----------


def test_datasource_create_and_http_reference(db_session):
    datasource_service.create_datasource(
        db_session,
        name="高德天气",
        base_url="https://restapi.amap.com/v3/weather/weatherInfo",
        method="GET",
        headers={"key": "gaode-key"},
    )
    agent = agent_service.create_agent(db_session, name="天气助手", created_by="tester")
    v1 = agent_service.list_versions(db_session, agent.id)[0]
    wf = {
        "start": "fetch",
        "steps": {
            "fetch": {
                "type": "http",
                "datasource": "高德天气",
                "params": {"city": "北京"},
                "save_as": "w",
                "next": "end",
            },
            "end": {"type": "end"},
        },
    }
    # 数据源存在 → update_draft 通过（DATASOURCE_MISSING 不触发）
    v1 = agent_service.update_draft(db_session, v1.id, prompt="p", workflow_config=wf)
    assert v1.status == "draft"
    assert datasource_service.get_datasource(db_session, "高德天气").base_url.endswith("weatherInfo")


# ---------- 验收：创建能力 → 绑定到草稿 → 把某 llm 节点沉淀为新能力 ----------


def test_capability_flow(db_session):
    capability_service.create_capability(
        db_session, name="满意度判断", description="判断用户满意度", behavior_instruction="判断用户反馈的满意度"
    )
    agent = agent_service.create_agent(db_session, name="助手", created_by="tester")
    v1 = agent_service.list_versions(db_session, agent.id)[0]
    v1 = capability_service.bind_capability(db_session, v1.id, "满意度判断", {"active": True})
    assert v1.capability_bindings["满意度判断"]["active"] is True

    # 沉淀：把 workflow 里的 llm 节点存为能力
    v1 = agent_service.update_draft(db_session, v1.id, prompt="p", workflow_config=SAMPLE_WORKFLOW)
    cap = capability_service.save_as_capability(db_session, v1.id, "coupon_offer", name="发优惠券话术")
    assert cap.behavior_instruction == SAMPLE_WORKFLOW["steps"]["coupon_offer"]["prompt"]


# ---------- 验收：KNOWLEDGE_BINDING_MISSING / DATASOURCE_MISSING 校验生效 ----------


def test_knowledge_binding_missing_allows_save_but_blocks_publish(db_session):
    """保存不拦（逻辑问题留到发布时提醒）；发布拦 KNOWLEDGE_BINDING_MISSING。"""
    agent = agent_service.create_agent(db_session, name="助手", created_by="tester")
    v1 = agent_service.list_versions(db_session, agent.id)[0]
    v1.knowledge_bindings = ["不存在的知识"]
    db_session.commit()
    v1 = agent_service.update_draft(db_session, v1.id, prompt="p", workflow_config=SAMPLE_WORKFLOW)
    assert v1.status == "draft"  # 保存成功
    with pytest.raises(PublishError):
        publish_service.publish(db_session, v1.id, approved_by="tester")


def test_datasource_missing_allows_save_but_blocks_publish(db_session):
    """保存不拦（逻辑问题留到发布时提醒）；发布拦 DATASOURCE_MISSING。"""
    agent = agent_service.create_agent(db_session, name="助手", created_by="tester")
    v1 = agent_service.list_versions(db_session, agent.id)[0]
    wf = {
        "start": "fetch",
        "steps": {
            "fetch": {"type": "http", "datasource": "不存在的数据源", "save_as": "w", "next": "end"},
            "end": {"type": "end"},
        },
    }
    v1 = agent_service.update_draft(db_session, v1.id, prompt="p", workflow_config=wf)
    assert v1.status == "draft"  # 保存成功
    with pytest.raises(PublishError):
        publish_service.publish(db_session, v1.id, approved_by="tester")
