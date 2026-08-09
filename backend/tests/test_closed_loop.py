"""Layer 5 验收：反馈 → generate_plan → apply_plan → 新 draft 通过校验 → publish（闭环）。"""

import pytest
from sqlalchemy.orm import Session

from app.core.llm_schemas import Change, ModificationPlan
from app.models.agent import Agent
from app.models.plan import ModificationPlan as PlanModel
from app.models.trace import Trace
from app.services import agent_service, analysis_service, optimization_service, publish_service
from tests.sample_data import SAMPLE_WORKFLOW


def _publish_plan_result() -> ModificationPlan:
    return ModificationPlan(
        problem_analysis="回复缺少个性化",
        root_cause="问题收集节点 prompt 未要求引用前文",
        suggestions=["更新问题收集节点 prompt，要求引用用户前文细节"],
        changes=[
            Change(
                target="workflow",
                operation="update_node",
                path="steps.problem_collection",
                value={"prompt": "用开放式问题引导用户说出具体不满，并引用用户前文提到过的细节"},
                description="更新问题收集节点 prompt",
            )
        ],
    )


@pytest.mark.asyncio
async def test_closed_loop(monkeypatch, db_session: Session):
    # 1) 创建 Agent → 更新草稿 → 发布 V1
    agent = agent_service.create_agent(db_session, name="餐后体验回访助手", created_by="tester")
    v1 = agent_service.list_versions(db_session, agent.id)[0]
    v1 = agent_service.update_draft(
        db_session, v1.id, prompt="你是餐后体验回访助手", workflow_config=SAMPLE_WORKFLOW
    )
    v1 = publish_service.publish(db_session, v1.id, approved_by="tester")
    assert agent_service.get_version(db_session, v1.id).status == "published"

    # 2) 建一条运行 Trace
    trace = Trace(
        agent_id=agent.id,
        version_id=v1.id,
        env="test",
        input="今天吃饭感觉一般",
        steps=[],
        output="感谢您的反馈",
        model="deepseek/deepseek-v4-flash",
    )
    db_session.add(trace)
    db_session.commit()
    db_session.refresh(trace)

    # 3) 打反馈
    fb = analysis_service.add_feedback(db_session, trace.id, "回复太机械，没有追问原因", "tester")

    # 4) mock call_structured 返回方案
    plan_result = _publish_plan_result()

    async def fake_call_structured(schema, system, user, max_retries=3, model="primary"):
        return plan_result

    monkeypatch.setattr(optimization_service, "call_structured", fake_call_structured)

    # 5) generate_plan
    plan = await optimization_service.generate_plan(db_session, fb.id)
    assert plan.status == "pending"
    assert plan.agent_id == agent.id
    assert plan.changes  # 非空

    # 6) apply_plan → 新 draft V2，配置已变更且通过校验
    v2 = optimization_service.apply_plan(db_session, plan.id, approved_by="tester")
    assert v2.version_no == 2
    assert v2.status == "draft"
    assert (
        v2.workflow_config["steps"]["problem_collection"]["prompt"]
        == "用开放式问题引导用户说出具体不满，并引用用户前文提到过的细节"
    )
    plan_row = db_session.get(PlanModel, plan.id)
    assert plan_row.status == "applied"
    assert plan_row.applied_version_id == v2.id

    # 7) 发布 V2 → 线上切换
    v2 = publish_service.publish(db_session, v2.id, approved_by="tester")
    assert v2.status == "published"
    assert db_session.get(Agent, agent.id).current_version_id == v2.id


def test_apply_plan_rejects_invalid_changes(db_session: Session):
    """AI 生成断掉的图 → apply_plan 拒绝并回滚（不产生新版本）。"""
    agent = agent_service.create_agent(db_session, name="回访", created_by="tester")
    v1 = agent_service.list_versions(db_session, agent.id)[0]
    v1 = agent_service.update_draft(
        db_session, v1.id, prompt="你是回访助手", workflow_config=SAMPLE_WORKFLOW
    )
    publish_service.publish(db_session, v1.id, approved_by="tester")

    trace = Trace(
        agent_id=agent.id, version_id=v1.id, env="test", input="一般", steps=[], output="回复",
        model="deepseek/deepseek-v4-flash",
    )
    db_session.add(trace)
    db_session.commit()
    db_session.refresh(trace)
    fb = analysis_service.add_feedback(db_session, trace.id, "坏方案", "tester")

    # 方案：删掉 end 节点 → 校验会报 MISSING_END → 拒绝
    bad_plan = ModificationPlan(
        problem_analysis="x", root_cause="y", suggestions=["z"],
        changes=[Change(target="workflow", operation="remove_node", path="steps.end", description="删掉 end")],
    )

    async def fake_call_structured(schema, system, user, max_retries=3, model="primary"):
        return bad_plan

    # 直接 mock 后调 generate_plan 麻烦，这里直接构造一个 pending plan 记录
    from app.models.plan import ModificationPlan as PlanModel

    plan = PlanModel(
        feedback_id=fb.id,
        agent_id=agent.id,
        problem_analysis="x",
        root_cause="y",
        suggestions=["z"],
        changes=[c.model_dump() for c in bad_plan.changes],
        status="pending",
    )
    db_session.add(plan)
    db_session.commit()
    db_session.refresh(plan)

    before_count = len(agent_service.list_versions(db_session, agent.id))
    with pytest.raises(optimization_service.OptimizationError):
        optimization_service.apply_plan(db_session, plan.id, approved_by="tester")
    db_session.rollback()  # apply_plan 内已 rollback；这里确保会话干净
    after_count = len(agent_service.list_versions(db_session, agent.id))
    assert after_count == before_count  # 没有留下脏 draft
    plan_row = db_session.get(PlanModel, plan.id)
    assert plan_row.status == "pending"  # 失败不置 applied
