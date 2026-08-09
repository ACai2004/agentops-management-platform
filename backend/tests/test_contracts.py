"""Layer 1 验收：核心契约能通过 Pydantic 校验（蓝图 §5.1 示例 workflow_config 必须可校验）。"""

import pytest
from pydantic import ValidationError

from app.core.contracts import (
    AgentConfig,
    ModelSettings,
    TraceRecord,
    TraceStep,
    WorkflowConfig,
    WorkflowNode,
)
from app.core.llm_schemas import Change, DecisionOutput, ModificationPlan
from tests.sample_data import SAMPLE_WORKFLOW


def test_sample_workflow_config_validates():
    """验收标准：示例 workflow_config 能通过 WorkflowConfig.model_validate。"""
    wf = WorkflowConfig.model_validate(SAMPLE_WORKFLOW)
    assert wf.start == "understanding"
    assert set(wf.steps) == {
        "understanding",
        "satisfaction_check",
        "coupon_offer",
        "problem_collection",
        "end",
    }
    assert wf.steps["satisfaction_check"].type == "decision"
    assert wf.steps["satisfaction_check"].branches == {
        "satisfied": "coupon_offer",
        "neutral": "problem_collection",
        "unsatisfied": "problem_collection",
    }
    assert wf.steps["end"].type == "end"


def test_agent_config_validates_with_defaults():
    cfg = AgentConfig(
        prompt="你是餐后体验回访助手",
        workflow=WorkflowConfig.model_validate(SAMPLE_WORKFLOW),
    )
    assert cfg.prompt == "你是餐后体验回访助手"
    assert cfg.model_settings.model == "deepseek/deepseek-v4-flash"
    assert cfg.capability_bindings == {}


def test_agent_config_with_model_override_and_bindings():
    cfg = AgentConfig(
        prompt="p",
        workflow=WorkflowConfig.model_validate(SAMPLE_WORKFLOW),
        capability_bindings={"满意度判断": {"active": True}},
        model_settings=ModelSettings(model="deepseek/deepseek-chat", temperature=0.0),
    )
    assert cfg.model_settings.temperature == 0.0
    assert cfg.capability_bindings["满意度判断"]["active"] is True


def test_workflow_node_minimal_end():
    node = WorkflowNode(type="end")
    assert node.prompt is None
    assert node.next is None
    assert node.branches is None
    assert node.model_settings is None


def test_invalid_node_type_rejected():
    with pytest.raises(ValidationError):
        WorkflowNode(type="unknown")


def test_invalid_workflow_config_rejected():
    with pytest.raises(ValidationError):
        WorkflowConfig.model_validate({"start": "a", "steps": {"a": {"type": "bogus"}}})


def test_trace_step_and_record_validates():
    step = TraceStep(
        node_id="understanding",
        node_type="llm",
        output="你好，能和我聊聊今天的用餐体验吗？",
        model="deepseek/deepseek-chat",
        token_usage={"prompt_tokens": 120, "completion_tokens": 30, "total_tokens": 150},
        latency_ms=812.5,
    )
    record = TraceRecord(
        trace_id="trace-1",
        agent_id="agent-1",
        version_id="version-1",
        env="test",
        input="今天吃饭感觉一般。",
        steps=[step],
        output="你好，能和我聊聊今天的用餐体验吗？",
        model="deepseek/deepseek-chat",
        created_at="2026-08-06T00:00:00Z",
    )
    assert record.env == "test"
    assert record.steps[0].node_type == "llm"
    assert record.steps[0].token_usage["total_tokens"] == 150
    assert record.steps[0].latency_ms == 812.5


def test_llm_schemas_decision_output():
    decision = DecisionOutput(choice="satisfied")
    assert decision.choice == "satisfied"


def test_llm_schemas_modification_plan():
    change = Change(
        target="workflow",
        operation="add_node",
        path="steps.refund_check",
        value={
            "type": "decision",
            "prompt": "判断用户是否有退款意图，只输出 JSON：{\"choice\": \"yes\" | \"no\"}",
            "save_as": "refund_intent",
            "branches": {"yes": "refund_handling", "no": "end"},
        },
        description="新增退款意图判断分支",
    )
    plan = ModificationPlan(
        problem_analysis="用户表达退款需求但 Agent 直接结束对话",
        root_cause="Workflow 缺少退款意图判断分支",
        suggestions=["新增退款意图判断", "新增退款处理话术"],
        changes=[change],
    )
    assert plan.problem_analysis != ""
    assert plan.changes[0].operation == "add_node"
    assert plan.changes[0].target == "workflow"


def test_llm_schemas_change_requires_description():
    with pytest.raises(ValidationError):
        Change(target="prompt", operation="replace", path="prompt", value="新提示词")
