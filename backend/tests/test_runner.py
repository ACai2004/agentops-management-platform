"""Layer 3 验收：run_agent 执行种子 workflow，产出非空 Trace（含 llm/decision 节点、branch 正确）。

用 mock LLM 保证确定性、CI 稳定（真实 LLM 端到端验证见 Layer 3 验收）。
"""

import pytest

from app.core.contracts import AgentConfig, WorkflowConfig
from app.core.llm_schemas import DecisionOutput
from app.runtime import nodes
from app.runtime.runner import run_agent
from tests.sample_data import SAMPLE_WORKFLOW


def _make_config() -> AgentConfig:
    return AgentConfig(
        prompt="你是餐后体验回访助手",
        workflow=WorkflowConfig.model_validate(SAMPLE_WORKFLOW),
    )


@pytest.mark.asyncio
async def test_run_agent_produces_trace_with_llm_and_decision(monkeypatch):
    """验收核心：跑 run_agent，Trace 非空且含 llm/decision 节点、branch 正确。"""

    async def fake_call(messages, model="primary", temperature=0.7, max_tokens=1024, json_mode=False):
        return "感谢您的反馈，我们很重视您的用餐体验。"

    async def fake_call_structured(schema, system, user, max_retries=3, model="primary"):
        return DecisionOutput(choice="unsatisfied")

    monkeypatch.setattr(nodes, "call", fake_call)
    monkeypatch.setattr(nodes, "call_structured", fake_call_structured)

    trace = await run_agent(_make_config(), "今天吃饭感觉一般", env="test")

    assert trace.output  # 非空
    assert trace.steps  # 非空
    types = [s.node_type for s in trace.steps]
    assert "llm" in types and "decision" in types and "end" in types

    decision_step = next(s for s in trace.steps if s.node_type == "decision")
    assert decision_step.branch == "unsatisfied"
    assert trace.env == "test"
    assert trace.input == "今天吃饭感觉一般"

    # 执行顺序：understanding -> satisfaction_check -> problem_collection -> end
    assert [s.node_id for s in trace.steps] == [
        "understanding",
        "satisfaction_check",
        "problem_collection",
        "end",
    ]


@pytest.mark.asyncio
async def test_run_agent_invalid_branch_falls_back_to_end(monkeypatch):
    """decision 返回不在 branches 里的 choice -> 路由兜底到 end 节点。"""

    async def fake_call(messages, model="primary", temperature=0.7, max_tokens=1024, json_mode=False):
        return "回复"

    async def fake_call_structured(schema, system, user, max_retries=3, model="primary"):
        return DecisionOutput(choice="unknown_choice")

    monkeypatch.setattr(nodes, "call", fake_call)
    monkeypatch.setattr(nodes, "call_structured", fake_call_structured)

    trace = await run_agent(_make_config(), "今天吃饭感觉一般", env="test")

    assert trace.steps[-1].node_type == "end"
    decision_step = next(s for s in trace.steps if s.node_type == "decision")
    assert decision_step.branch is None  # 非法 choice 被置 None，兜底到 end
