"""LangGraph 节点实现：llm / decision / end（§9.3）。

每个节点执行时都记录 TraceStep 追加到 state["trace_steps"]（§6 运行规则）。
"""

import time
from collections.abc import Callable

from app.core.config import settings
from app.core.contracts import TraceStep, WorkflowNode
from app.core.llm_schemas import DecisionOutput
from app.llm.client import call
from app.llm.structured import call_structured
from app.runtime.agent_state import AgentState


def _resolve_model(node: WorkflowNode, state: AgentState) -> str:
    """解析节点实际使用的模型：节点级覆盖 > Agent 级默认 > 全局配置。"""
    if node.model_settings is not None and node.model_settings.model:
        return node.model_settings.model
    agent_settings = state["agent_config"].get("model_settings") or {}
    return agent_settings.get("model") or settings.llm_model


def _build_messages(node: WorkflowNode, state: AgentState) -> list[dict]:
    """llm 节点：AgentConfig.prompt + 节点 prompt 组装系统消息，上下文 + 前序产物组装用户消息。"""
    agent_prompt = state["agent_config"].get("prompt", "")
    system_parts = [p for p in (agent_prompt, node.prompt) if p]
    system = "\n\n".join(system_parts)

    user_parts = []
    if state.get("input"):
        user_parts.append(f"用户输入：{state['input']}")
    for key, value in state["vars"].items():
        if value is not None and value != "":
            user_parts.append(f"「{key}」：{value}")
    user = "\n".join(user_parts) if user_parts else "（无额外上下文）"

    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]


def _build_decision_prompt(node: WorkflowNode, state: AgentState) -> str:
    """decision 节点：判断指令 + 上下文组装成 user 消息。"""
    parts = [f"判断指令：{node.prompt}"] if node.prompt else []
    if state.get("input"):
        parts.append(f"用户输入：{state['input']}")
    for key, value in state["vars"].items():
        if value is not None and value != "":
            parts.append(f"「{key}」：{value}")
    return "\n".join(parts)


def _short_context(state: AgentState, limit: int = 120) -> str:
    """TraceStep.input 的简短上下文。"""
    return state.get("input", "")[:limit]


def _messages_to_text(messages: list[dict]) -> str:
    return "\n".join(f"{m['role']}: {m['content']}" for m in messages)


def make_llm_node(node_id: str, node: WorkflowNode) -> Callable:
    async def _node(state: AgentState) -> AgentState:
        started = time.perf_counter()
        messages = _build_messages(node, state)
        content = await call(messages, json_mode=False)
        if node.save_as:
            state["vars"][node.save_as] = content
        state["trace_steps"].append(
            TraceStep(
                node_id=node_id,
                node_type="llm",
                input=_short_context(state),
                output=content,
                model=_resolve_model(node, state),
                prompt=_messages_to_text(messages),
                latency_ms=(time.perf_counter() - started) * 1000,
            ).model_dump()
        )
        return state

    return _node


def make_decision_node(node_id: str, node: WorkflowNode) -> Callable:
    async def _node(state: AgentState) -> AgentState:
        started = time.perf_counter()
        system = state["agent_config"].get("prompt", "")
        user = _build_decision_prompt(node, state)
        result = await call_structured(
            DecisionOutput,
            system=system,
            user=user,
        )
        # 分支不在 branches 时置 None，路由层兜底到 end
        choice = result.choice if result.choice in (node.branches or {}) else None
        if node.save_as:
            state["vars"][node.save_as] = {"choice": choice}
        state["trace_steps"].append(
            TraceStep(
                node_id=node_id,
                node_type="decision",
                output={"choice": choice},
                branch=choice,
                model=_resolve_model(node, state),
                latency_ms=(time.perf_counter() - started) * 1000,
            ).model_dump()
        )
        return state

    return _node


def make_end_node(node_id: str) -> Callable:
    async def _node(state: AgentState) -> AgentState:
        # 优先取 vars["output"]，否则取最后一个非空字符串产物
        output = state["vars"].get("output")
        if not output:
            for value in reversed(list(state["vars"].values())):
                if isinstance(value, str) and value.strip():
                    output = value
                    break
        state["output"] = output or state.get("input", "")
        state["trace_steps"].append(
            TraceStep(node_id=node_id, node_type="end", output=state["output"]).model_dump()
        )
        return state

    return _node
