"""template 节点验收：通用文本模板（确定性拼接，对应 Dify 模板转换 / Langflow Prompt）+ 校验规则。"""

import pytest

from app.core.contracts import AgentConfig, WorkflowConfig
from app.core.workflow_validation import validate_workflow
from app.runtime import nodes
from app.runtime.runner import run_agent


def _template_config() -> AgentConfig:
    return AgentConfig(
        prompt="你是餐后回访 AI。",
        workflow=WorkflowConfig.model_validate(
            {
                "start": "llm1",
                "steps": {
                    "llm1": {"type": "llm", "prompt": "理解", "save_as": "order", "next": "tpl"},
                    "tpl": {
                        "type": "template",
                        "template": "{{system_prompt}}\n\n---\n\n【订单】{{order}}",
                        "save_as": "output",
                        "next": "end",
                    },
                    "end": {"type": "end"},
                },
            }
        ),
    )


def test_template_missing_save_as_is_error():
    cfg = AgentConfig(
        prompt="p",
        workflow=WorkflowConfig.model_validate(
            {
                "start": "tpl",
                "steps": {
                    "tpl": {"type": "template", "template": "x", "next": "end"},
                    "end": {"type": "end"},
                },
            }
        ),
    )
    issues = validate_workflow(cfg)
    assert any(i.code == "TEMPLATE_MISSING_SAVE_AS" and i.severity == "error" for i in issues)


def test_template_valid_config_clean():
    issues = validate_workflow(_template_config())
    assert not any(i.code.startswith("TEMPLATE_") and i.severity == "error" for i in issues)


@pytest.mark.asyncio
async def test_template_interpolates_system_prompt_and_vars(monkeypatch):
    captured = {}

    async def fake_call(messages, model="primary", temperature=0.7, max_tokens=1024, json_mode=False):
        captured["messages"] = messages
        return '{"restaurant": "売泰"}'

    monkeypatch.setattr(nodes, "call", fake_call)

    trace = await run_agent(_template_config(), "识别小票", env="test")
    output = trace.output
    assert "你是餐后回访 AI。" in output        # {{system_prompt}} 注入静态提示
    assert "【订单】" in output
    assert '{"restaurant": "売泰"}' in output   # {{order}} 注入前序产物
    # template 步骤已记录（确定性，不调用 LLM）
    tpl_step = next(s for s in trace.steps if s.node_type == "template")
    assert tpl_step.output == output
