"""Layer 5 验收：四层校验规则（最小 workflow 通过 + 每个 code 一个违规用例 + 种子 workflow 零问题）。"""

from app.core.config import settings
from app.core.contracts import AgentConfig, ModelSettings, WorkflowConfig
from app.core.workflow_validation import validate_workflow
from tests.sample_data import SAMPLE_WORKFLOW

MINIMAL = {"start": "end", "steps": {"end": {"type": "end"}}}


def _config(workflow_dict, prompt="p", model_settings=None) -> AgentConfig:
    return AgentConfig(
        prompt=prompt,
        workflow=WorkflowConfig.model_validate(workflow_dict),
        model_settings=model_settings or ModelSettings(),
    )


def _issues(cfg, existing_datasources=None):
    return validate_workflow(cfg, existing_datasources=existing_datasources)


# ---------- 验收：最小 workflow 通过 ----------


def test_minimal_workflow_passes():
    assert _issues(_config(MINIMAL)) == []


# ---------- 验收：种子 workflow 零问题 ----------


def test_seed_workflow_zero_issues():
    assert _issues(_config(SAMPLE_WORKFLOW)) == []


# ---------- Layer 2 · Topology ----------


def test_missing_start():
    issues = _issues(_config({"start": "nope", "steps": {"end": {"type": "end"}}}))
    assert any(i.code == "MISSING_START" and i.severity == "error" for i in issues)


def test_dangling_edge():
    wf = {
        "start": "a",
        "steps": {
            "a": {"type": "llm", "prompt": "x", "save_as": "y", "next": "ghost"},
            "end": {"type": "end"},
        },
    }
    issues = _issues(_config(wf))
    assert any(i.code == "DANGLING_EDGE" and i.node_id == "a" for i in issues)


def test_cycle():
    wf = {
        "start": "a",
        "steps": {
            "a": {"type": "llm", "prompt": "x", "save_as": "y", "next": "b"},
            "b": {"type": "llm", "prompt": "x", "save_as": "z", "next": "a"},
        },
    }
    issues = _issues(_config(wf))
    assert any(i.code == "CYCLE" and i.severity == "error" for i in issues)


def test_missing_end():
    wf = {"start": "a", "steps": {"a": {"type": "llm", "prompt": "x", "save_as": "y", "next": "a"}}}
    issues = _issues(_config(wf))
    assert any(i.code == "MISSING_END" for i in issues)


def test_unreachable_node():
    wf = {
        "start": "a",
        "steps": {
            "a": {"type": "llm", "prompt": "x", "save_as": "y", "next": "end"},
            "orphan": {"type": "llm", "prompt": "x", "save_as": "z", "next": "end"},
            "end": {"type": "end"},
        },
    }
    issues = _issues(_config(wf))
    assert any(i.code == "UNREACHABLE_NODE" and i.node_id == "orphan" for i in issues)


# ---------- Layer 3A · Semantic 节点字段 ----------


def test_missing_prompt():
    wf = {"start": "a", "steps": {"a": {"type": "llm", "save_as": "y", "next": "end"}, "end": {"type": "end"}}}
    issues = _issues(_config(wf))
    assert any(i.code == "MISSING_PROMPT" for i in issues)


def test_decision_missing_save_as_is_error():
    wf = {
        "start": "a",
        "steps": {"a": {"type": "decision", "prompt": "x", "branches": {"x": "end"}}, "end": {"type": "end"}},
    }
    issues = _issues(_config(wf))
    assert any(i.code == "MISSING_SAVE_AS" and i.severity == "error" for i in issues)


def test_empty_branches():
    wf = {
        "start": "a",
        "steps": {"a": {"type": "decision", "prompt": "x", "save_as": "s", "branches": {}}, "end": {"type": "end"}},
    }
    issues = _issues(_config(wf))
    assert any(i.code == "EMPTY_BRANCHES" for i in issues)


def test_llm_missing_next_warning():
    wf = {"start": "a", "steps": {"a": {"type": "llm", "prompt": "x", "save_as": "y"}, "end": {"type": "end"}}}
    issues = _issues(_config(wf))
    assert any(i.code == "LLM_MISSING_NEXT" and i.severity == "warning" for i in issues)


def test_end_has_next_warning():
    wf = {
        "start": "a",
        "steps": {"a": {"type": "llm", "prompt": "x", "save_as": "y", "next": "end"}, "end": {"type": "end", "next": "a"}},
    }
    issues = _issues(_config(wf))
    assert any(i.code == "END_HAS_NEXT" and i.severity == "warning" for i in issues)


def test_http_rules():
    wf = {
        "start": "fetch",
        "steps": {
            "fetch": {"type": "http", "datasource": "weather", "save_as": "w", "next": "end"},
            "end": {"type": "end"},
        },
    }
    # 数据源存在 → 无 DATASOURCE_MISSING；数据源缺失 → 报错
    assert not any(i.code == "DATASOURCE_MISSING" for i in _issues(_config(wf), existing_datasources={"weather"}))
    assert any(i.code == "DATASOURCE_MISSING" for i in _issues(_config(wf), existing_datasources=set()))
    # http 缺 save_as / next
    wf2 = {
        "start": "fetch",
        "steps": {"fetch": {"type": "http", "datasource": "weather"}, "end": {"type": "end"}},
    }
    issues2 = _issues(_config(wf2), existing_datasources={"weather"})
    assert any(i.code == "HTTP_MISSING_SAVE_AS" for i in issues2)
    assert any(i.code == "HTTP_MISSING_NEXT" for i in issues2)


def test_http_required_param():
    """数据源声明必填参数 → 节点 params 未配置 → error（拦住保存/发布）。"""
    ds = {"weather": {"param_defs": [{"name": "city", "label": "城市编码", "required": True, "type": "text"}]}}
    wf = {
        "start": "fetch",
        "steps": {
            "fetch": {"type": "http", "datasource": "weather", "params": {}, "save_as": "w", "next": "end"},
            "end": {"type": "end"},
        },
    }
    issues = _issues(_config(wf), existing_datasources=ds)
    assert any(i.code == "HTTP_MISSING_REQUIRED_PARAM" and i.severity == "error" for i in issues)
    # 配置了必填参数 → 干净
    wf2 = {
        "start": "fetch",
        "steps": {
            "fetch": {"type": "http", "datasource": "weather", "params": {"city": "{{adcode}}"}, "save_as": "w", "next": "end"},
            "end": {"type": "end"},
        },
    }
    issues2 = _issues(_config(wf2), existing_datasources=ds)
    assert not any(i.code == "HTTP_MISSING_REQUIRED_PARAM" for i in issues2)


# ---------- Layer 3B · 模型能力 ----------


def test_image_input_requires_vision_model():
    wf = {
        "start": "a",
        "steps": {
            "a": {"type": "llm", "prompt": "x", "save_as": "y", "next": "end", "image_input": True},
            "end": {"type": "end"},
        },
    }
    # 默认模型 deepseek（不支持视觉）→ MODEL_CAPABILITY_MISMATCH
    issues = _issues(_config(wf))
    assert any(i.code == "MODEL_CAPABILITY_MISMATCH" for i in issues)
    # Agent 级绑定视觉模型 → 通过
    cfg_vision = _config(wf, model_settings=ModelSettings(model=settings.vision_model))
    assert not any(i.code == "MODEL_CAPABILITY_MISMATCH" for i in _issues(cfg_vision))
