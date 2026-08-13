"""Layer 2 验收：结构化输出通道的重试/回喂逻辑。

用 mock 的 call 保证确定性，CI 稳定且不消耗 API。
（真实 LLM 验证见 Layer 2 验收 —— 用真实 DeepSeek key 跑 call_structured。）
"""

import pytest
from pydantic import BaseModel

from app.core.llm_schemas import DecisionOutput
from app.llm import client, structured
from app.llm.structured import StructuredOutputError, call_structured


class _FakeSchema(BaseModel):
    value: int


def _fake_call_sequence(results, calls):
    """构造一个按顺序返回给定结果的异步 call，并记录每次调用收到的 messages。"""

    async def fake_call(messages, model="primary", temperature=0.7, max_tokens=1024, json_mode=False):
        calls.append(messages)
        idx = min(len(calls) - 1, len(results) - 1)
        return results[idx]

    return fake_call


@pytest.mark.asyncio
async def test_first_try_valid(monkeypatch):
    calls = []
    monkeypatch.setattr(structured, "call", _fake_call_sequence(['{"value": 42}'], calls))
    result = await call_structured(_FakeSchema, system="s", user="u")
    assert result.value == 42
    assert len(calls) == 1


@pytest.mark.asyncio
async def test_retries_on_bad_json(monkeypatch):
    """第一次返回坏 JSON -> 触发回喂重试 -> 第二次返回合法对象。"""
    calls = []
    monkeypatch.setattr(structured, "call", _fake_call_sequence(["not json", '{"value": 7}'], calls))
    result = await call_structured(_FakeSchema, system="s", user="u")
    assert result.value == 7
    assert len(calls) == 2
    # 第二次调用应带上校验错误回喂信息
    assert "无法通过校验" in calls[1][1]["content"]


@pytest.mark.asyncio
async def test_retries_on_validation_error(monkeypatch):
    """value 期望 int，第一次给字符串 -> ValidationError -> 重试成功。"""
    calls = []
    monkeypatch.setattr(
        structured, "call", _fake_call_sequence(['{"value": "not_int"}', '{"value": 1}'], calls)
    )
    result = await call_structured(_FakeSchema, system="s", user="u")
    assert result.value == 1
    assert len(calls) == 2


@pytest.mark.asyncio
async def test_raises_after_max_retries(monkeypatch):
    """连续坏输出 -> 达到 max_retries 后抛 StructuredOutputError。"""
    calls = []
    monkeypatch.setattr(structured, "call", _fake_call_sequence(["garbage"], calls))
    with pytest.raises(StructuredOutputError):
        await call_structured(_FakeSchema, system="s", user="u", max_retries=3)
    assert len(calls) == 3


@pytest.mark.asyncio
async def test_decision_output_with_real_schema(monkeypatch):
    """用平台真实的 DecisionOutput schema 走一遍（mock 返回合法 choice）。"""
    calls = []
    monkeypatch.setattr(structured, "call", _fake_call_sequence(['{"choice": "unsatisfied"}'], calls))
    result = await call_structured(DecisionOutput, system="s", user="u")
    assert result.choice == "unsatisfied"


@pytest.mark.asyncio
async def test_json_mode_injects_json_keyword(monkeypatch):
    """回归：DeepSeek 要求 response_format=json_object 时 prompt 里必须有 'json' 字样。

    判断分支提示词没写 json 时，网关要自动补引导，否则 DeepSeek 报 BadRequestError。
    """
    captured = {}

    async def fake_acompletion(model, messages, temperature, max_tokens, response_format):
        captured["messages"] = messages

        class _Content:
            content = '{"choice": "退货"}'

        class _Msg:
            message = _Content()

        class _Resp:
            choices = [_Msg()]

        return _Resp()

    monkeypatch.setattr(client.router, "acompletion", fake_acompletion)
    out = await client.call(
        [{"role": "system", "content": "s"}, {"role": "user", "content": "判断客户意图"}],
        json_mode=True,
    )
    sent = " ".join(str(m["content"]) for m in captured["messages"])
    assert "json" in sent.lower()  # 自动补了 JSON 引导，且确实用了 response_format
    assert out == '{"choice": "退货"}'
