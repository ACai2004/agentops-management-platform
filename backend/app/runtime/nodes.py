"""LangGraph 节点实现：llm / decision / end / http（§9.3）。

每个节点执行时都记录 TraceStep 追加到 state["trace_steps"]（§6 运行规则）。
"""

import asyncio
import time
from collections.abc import Callable
from urllib.parse import parse_qsl, urlencode, urlparse

import httpx

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


def _router_model(node: WorkflowNode, state: AgentState) -> str:
    """把解析出的模型映射到 LiteLLM Router 的 model_name（primary / vision）。"""
    if _resolve_model(node, state) == settings.vision_model:
        return "vision"
    return "primary"


def _interpolate(template: str, state: AgentState) -> str:
    """把 {{var}} 替换为 state.vars 中的值（http 节点的参数/URL 插值）。"""
    result = template
    for key, value in state["vars"].items():
        result = result.replace("{{" + str(key) + "}}", str(value))
    return result


def _build_url(base_url: str, params: dict | None, state: AgentState) -> str:
    """把 base_url 自带的 query 参数与节点 params（支持 {{var}} 插值）合并进 URL。

    注意：httpx 传 params 会丢弃 url 自带的 query（如 base_url 里的 ?key=...），
    所以这里手动解析并合并，避免数据源 key 丢失。
    """
    url = _interpolate(base_url, state)
    parsed = urlparse(url)
    merged = dict(parse_qsl(parsed.query))
    for k, v in (params or {}).items():
        value = _interpolate(str(v), state)
        if value:  # 空值参数不拼进 URL（如可选参数没填、{{变量}} 运行时没值）
            merged[k] = value
    return parsed._replace(query=urlencode(merged)).geturl()


def _system_context(state: AgentState, node_prompt: str | None = None) -> str:
    """系统消息 = Agent 提示词 + 绑定的知识内容 + 节点 prompt（§6 知识注入，实时引用）。"""
    agent_prompt = state["agent_config"].get("prompt", "")
    knowledge_parts = []
    for name in state["agent_config"].get("knowledge_bindings") or []:
        content = (state.get("knowledges") or {}).get(name)
        if content:
            knowledge_parts.append(f"【知识库「{name}」】\n{content}")
    parts = [p for p in (agent_prompt, *knowledge_parts, node_prompt) if p]
    return "\n\n".join(parts)


def _inputs_context(state: AgentState) -> str:
    """把命名输入渲染成 user 上下文（按 schema 的 label；image 类型不塞文本）。

    例如「小票照片」在视觉节点走 image content part，这里只放 text/number/select。
    """
    schema = (state.get("agent_config") or {}).get("workflow") or {}
    labels = {f.get("name"): (f.get("label") or f.get("name")) for f in (schema.get("inputs") or [])}
    image_names = {f.get("name") for f in (schema.get("inputs") or []) if f.get("type") == "image"}
    parts = []
    for name, value in (state.get("inputs") or {}).items():
        if name in image_names or value is None or value == "":
            continue
        parts.append(f"{labels.get(name, name)}：{value}")
    return "\n".join(parts)


def _build_messages(node: WorkflowNode, state: AgentState) -> list[dict]:
    """llm 节点：系统消息 = 提示词 + 知识 + 节点 prompt；用户消息 = 上下文 + 前序产物。

    `image_input=true` 时用户消息含图片 content part（OpenAI 兼容 content 数组）。
    """
    # llm 提示词支持 {{变量}} 插值（业务人员可显式引用前序产物）
    node_prompt = _interpolate(node.prompt, state) if node.prompt else node.prompt
    system = _system_context(state, node_prompt)

    user_parts = []
    inputs_context = _inputs_context(state)
    if inputs_context:
        user_parts.append(inputs_context)
    elif state.get("input"):
        # 兼容：无命名输入时的旧路径
        user_parts.append(f"用户输入：{state['input']}")
    for key, value in state["vars"].items():
        if value is not None and value != "":
            user_parts.append(f"「{key}」：{value}")
    user = "\n".join(user_parts) if user_parts else "（无额外上下文）"

    if node.image_input and state.get("image_url"):
        user_content: list = [
            {"type": "text", "text": user},
            {"type": "image_url", "image_url": {"url": state["image_url"]}},
        ]
        return [
            {"role": "system", "content": system},
            {"role": "user", "content": user_content},
        ]
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]


def _build_decision_prompt(node: WorkflowNode, state: AgentState) -> str:
    """decision 节点：判断指令 + 可选分支值 + 上下文组装成 user 消息。"""
    prompt = _interpolate(node.prompt, state) if node.prompt else None
    parts = [f"判断指令：{prompt}"] if prompt else []
    if node.branches:
        parts.append(f"可选分支值：{', '.join(node.branches.keys())}")
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
        model = _router_model(node, state)
        content = await call(messages, model=model, json_mode=False)
        # 空输出重试：DeepSeek 偶发返回空内容（限流/突发），重试并提示模型避免整条流断掉
        for attempt in range(5):
            if content:
                break
            await asyncio.sleep(min(1.5 * (attempt + 1), 6))
            msgs = list(messages)
            if msgs and msgs[-1]["role"] == "user" and isinstance(msgs[-1]["content"], str):
                msgs[-1] = {**msgs[-1], "content": msgs[-1]["content"] + "\n\n（你上次没有返回任何内容，请重新完整输出。）"}
            content = await call(msgs, model=model, json_mode=False)
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
        system = _system_context(state)
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


def make_http_node(node_id: str, node: WorkflowNode) -> Callable:
    """http 节点：查数据源 → params/url 插值 → HTTP 请求 → 响应存 vars → 记录 TraceStep。

    失败不中止：把 {"error": ...} 存进 vars[save_as] 并记录，Workflow 继续（§6）。
    """

    async def _node(state: AgentState) -> AgentState:
        started = time.perf_counter()
        ds = (state.get("datasources") or {}).get(node.datasource)
        result: dict | str
        if not ds:
            result = {"error": f"数据源 {node.datasource} 未配置"}
        else:
            url = _build_url(ds.get("base_url", ""), node.params, state)
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    resp = await client.request(
                        ds.get("method", "GET"),
                        url,
                        headers=ds.get("headers"),
                    )
                    resp.raise_for_status()
                try:
                    result = resp.json()
                except ValueError:
                    result = resp.text
            except Exception as e:  # noqa: BLE001 —— 外部 API 失败不中止
                result = {"error": f"请求失败：{e}"}
        if node.save_as:
            state["vars"][node.save_as] = result
        state["trace_steps"].append(
            TraceStep(
                node_id=node_id,
                node_type="http",
                input=node.datasource or "",
                output=result,
                latency_ms=(time.perf_counter() - started) * 1000,
            ).model_dump()
        )
        return state

    return _node


def make_template_node(node_id: str, node: WorkflowNode) -> Callable:
    """template 节点：纯函数模板拼接（确定性，不经过 LLM）。

    template 支持 {{system_prompt}}（Agent 静态系统提示）与 {{var}}（前序节点产物）。
    通用文本模板：可拼提示词、报告、格式化文本等（对应 Dify 模板转换 / Langflow Prompt）。
    对应 Java 版 PromptAssembler：Runtime Prompt = Static System Prompt + 分隔符 + Dynamic Context。
    """

    async def _node(state: AgentState) -> AgentState:
        started = time.perf_counter()
        template = node.template or ""
        agent_prompt = (state.get("agent_config") or {}).get("prompt", "")
        text = template.replace("{{system_prompt}}", agent_prompt)
        text = _interpolate(text, state)
        if node.save_as:
            state["vars"][node.save_as] = text
        state["trace_steps"].append(
            TraceStep(
                node_id=node_id,
                node_type="template",
                output=text,
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
