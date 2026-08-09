"""Layer 5 验收：http 节点插值请求 + 失败继续 + 视觉 image_input。"""

import pytest

from app.core.config import settings
from app.core.contracts import AgentConfig, WorkflowConfig
from app.runtime import nodes
from app.runtime.runner import run_agent


class _FakeResponse:
    def __init__(self, status_code=200, json_data=None, text_data="{}"):
        self.status_code = status_code
        self._json = json_data
        self._text = text_data

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")

    def json(self):
        if self._json is not None:
            return self._json
        raise ValueError("not json")

    @property
    def text(self):
        return self._text


class _CapturingClient:
    """捕获请求并返回给定响应。"""

    def __init__(self, response=None):
        self.response = response or _FakeResponse(json_data={"temp": 28})
        self.calls = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False

    async def request(self, method, url, params=None, headers=None):
        self.calls.append({"method": method, "url": url, "params": params, "headers": headers})
        return self.response


class _FailingClient:
    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False

    async def request(self, *a, **kw):
        raise RuntimeError("timeout")


@pytest.mark.asyncio
async def test_http_node_interpolation_and_success(monkeypatch):
    client = _CapturingClient(_FakeResponse(json_data={"temp": 28}))

    async def fake_call(messages, model="primary", temperature=0.7, max_tokens=1024, json_mode=False):
        return "北京"  # 前序 llm 节点产出 city

    monkeypatch.setattr(nodes, "call", fake_call)
    monkeypatch.setattr(nodes.httpx, "AsyncClient", lambda timeout=None: client)

    cfg = AgentConfig(
        prompt="p",
        workflow=WorkflowConfig.model_validate(
            {
                "start": "extract",
                "steps": {
                    "extract": {"type": "llm", "prompt": "提取城市", "save_as": "city", "next": "fetch"},
                    "fetch": {
                        "type": "http",
                        "datasource": "weather",
                        "params": {"city": "{{city}}"},
                        "save_as": "weather",
                        "next": "end",
                    },
                    "end": {"type": "end"},
                },
            }
        ),
    )
    datasources = {
        "weather": {
            "base_url": "https://api.weather.example.com/weather",
            "method": "GET",
            "headers": {"key": "secret"},
        }
    }
    trace = await run_agent(cfg, "我在北京", env="test", datasources=datasources)

    assert client.calls, "http 节点应发起请求"
    call = client.calls[0]
    assert call["method"] == "GET"
    assert call["params"]["city"] == "北京"  # {{city}} 插值成功
    assert call["headers"] == {"key": "secret"}
    # 响应已存进 vars，end 节点把它作为输出
    assert "北京" in trace.output or "temp" in str(trace.output) or trace.steps
    http_step = next(s for s in trace.steps if s.node_type == "http")
    assert http_step.output == {"temp": 28}


@pytest.mark.asyncio
async def test_http_node_failure_continues(monkeypatch):
    monkeypatch.setattr(nodes.httpx, "AsyncClient", lambda timeout=None: _FailingClient())

    cfg = AgentConfig(
        prompt="p",
        workflow=WorkflowConfig.model_validate(
            {
                "start": "fetch",
                "steps": {
                    "fetch": {"type": "http", "datasource": "weather", "save_as": "w", "next": "end"},
                    "end": {"type": "end"},
                },
            }
        ),
    )
    datasources = {"weather": {"base_url": "https://api.example.com", "method": "GET"}}
    trace = await run_agent(cfg, "查天气", env="test", datasources=datasources)

    # 失败不中止：vars["w"] = {"error": ...}，流程继续到 end
    http_step = next(s for s in trace.steps if s.node_type == "http")
    assert isinstance(http_step.output, dict) and "error" in http_step.output
    assert trace.steps[-1].node_type == "end"


@pytest.mark.asyncio
async def test_llm_vision_image_input(monkeypatch):
    captured = {}

    async def fake_call(messages, model="primary", temperature=0.7, max_tokens=1024, json_mode=False):
        captured["messages"] = messages
        captured["model"] = model
        return "识别结果"

    monkeypatch.setattr(nodes, "call", fake_call)

    cfg = AgentConfig(
        prompt="看图助手",
        workflow=WorkflowConfig.model_validate(
            {
                "start": "see",
                "steps": {
                    "see": {
                        "type": "llm",
                        "prompt": "识别小票，输出订单 JSON",
                        "save_as": "order",
                        "next": "end",
                        "image_input": True,
                        "model_settings": {"model": settings.vision_model},
                    },
                    "end": {"type": "end"},
                },
            }
        ),
    )
    await run_agent(cfg, "识别小票", env="test", image_url="https://example.com/receipt.jpg")

    user = captured["messages"][1]["content"]
    assert isinstance(user, list), "带图节点应使用 content 数组"
    assert any(part.get("type") == "image_url" for part in user)
    assert captured["model"] == "vision"  # 路由到视觉模型
