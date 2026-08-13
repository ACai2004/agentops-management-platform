"""输入节点（WorkflowConfig.inputs）验收：契约 / 校验 / 运行时注入 / 必填约束。"""

import pytest
from pydantic import ValidationError

from app.core.config import settings
from app.core.contracts import AgentConfig, InputField, WorkflowConfig
from app.core.workflow_validation import validate_workflow
from app.runtime import nodes
from app.runtime.runner import run_agent

# ---------- 契约 ----------


def test_workflow_config_with_inputs_validates():
    wf = WorkflowConfig.model_validate(
        {
            "start": "see",
            "steps": {"see": {"type": "end"}},
            "inputs": [
                {"name": "receipt_image", "label": "小票照片", "type": "image", "required": True},
                {"name": "user_text", "label": "补充文本", "type": "text"},
            ],
        }
    )
    assert wf.inputs[0].type == "image"
    assert wf.inputs[0].required is True
    assert wf.inputs[1].label == "补充文本"


def test_inputs_default_empty():
    wf = WorkflowConfig.model_validate({"start": "end", "steps": {"end": {"type": "end"}}})
    assert wf.inputs == []


def test_invalid_input_type_rejected():
    with pytest.raises(ValidationError):
        InputField(name="x", type="audio")


# ---------- 校验 ----------


def _config(inputs) -> AgentConfig:
    return AgentConfig(
        prompt="p",
        workflow=WorkflowConfig.model_validate({"start": "end", "steps": {"end": {"type": "end"}}, "inputs": inputs}),
    )


def test_input_duplicate_name_error():
    issues = validate_workflow(
        _config([InputField(name="a", type="text"), InputField(name="a", type="text")])
    )
    assert any(i.code == "INPUT_DUPLICATE_NAME" and i.severity == "error" for i in issues)


def test_input_empty_name_error():
    issues = validate_workflow(_config([InputField(name="", type="text")]))
    assert any(i.code == "INPUT_EMPTY_NAME" for i in issues)


def test_input_select_without_options_error():
    issues = validate_workflow(_config([InputField(name="s", type="select")]))
    assert any(i.code == "INPUT_SELECT_NO_OPTIONS" for i in issues)


def test_valid_inputs_no_issues():
    issues = validate_workflow(
        _config([InputField(name="a", type="text"), InputField(name="b", type="select", options=["x", "y"])])
    )
    assert not any(i.code.startswith("INPUT_") for i in issues)


# ---------- 运行时 ----------


def _vision_workflow_inputs():
    return AgentConfig(
        prompt="看图助手",
        workflow=WorkflowConfig.model_validate(
            {
                "start": "see",
                "steps": {
                    "see": {
                        "type": "llm",
                        "prompt": "识别小票",
                        "save_as": "order",
                        "next": "end",
                        "image_input": True,
                        "model_settings": {"model": settings.vision_model},
                    },
                    "end": {"type": "end"},
                },
                "inputs": [
                    {"name": "receipt_image", "label": "小票照片", "type": "image", "required": True},
                    {"name": "user_text", "label": "补充文本", "type": "text"},
                ],
            }
        ),
    )


@pytest.mark.asyncio
async def test_required_input_missing_raises(monkeypatch):
    async def fake_call(messages, model="primary", temperature=0.7, max_tokens=1024, json_mode=False):
        return "ok"

    monkeypatch.setattr(nodes, "call", fake_call)
    # 缺少必填的图片输入 -> 触发必填校验
    with pytest.raises(ValueError, match="缺少必填输入：小票照片"):
        await run_agent(_vision_workflow_inputs(), "", env="test", inputs={"user_text": "有人"})


@pytest.mark.asyncio
async def test_inputs_injected_into_user_message(monkeypatch):
    captured = {}

    async def fake_call(messages, model="primary", temperature=0.7, max_tokens=1024, json_mode=False):
        captured["messages"] = messages
        return "ok"

    monkeypatch.setattr(nodes, "call", fake_call)

    cfg = AgentConfig(
        prompt="p",
        workflow=WorkflowConfig.model_validate(
            {
                "start": "chat",
                "steps": {
                    "chat": {"type": "llm", "prompt": "聊天", "save_as": "output", "next": "end"},
                    "end": {"type": "end"},
                },
                "inputs": [{"name": "user_text", "label": "用户说的话", "type": "text"}],
            }
        ),
    )
    await run_agent(cfg, "", env="test", inputs={"user_text": "今天下雨"})

    user = captured["messages"][1]["content"]
    assert "用户说的话：今天下雨" in user  # 用 label 渲染，不是字段名


@pytest.mark.asyncio
async def test_image_input_from_named_input(monkeypatch):
    captured = {}

    async def fake_call(messages, model="primary", temperature=0.7, max_tokens=1024, json_mode=False):
        captured["messages"] = messages
        return "识别结果"

    monkeypatch.setattr(nodes, "call", fake_call)

    trace = await run_agent(
        _vision_workflow_inputs(),
        "",
        env="test",
        inputs={"receipt_image": "data:image/png;base64,AAA", "user_text": "加牛肉"},
    )
    user = captured["messages"][1]["content"]
    assert isinstance(user, list)  # 图片 content 数组
    assert any(p.get("type") == "image_url" for p in user)
    assert trace.inputs == {"receipt_image": "data:image/png;base64,AAA", "user_text": "加牛肉"}
