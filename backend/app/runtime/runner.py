"""运行入口（§9.4）：编译图 + 执行 + 产出 TraceRecord。"""

import uuid
from datetime import UTC, datetime

from langgraph.errors import GraphRecursionError

from app.core.config import settings
from app.core.contracts import AgentConfig, TraceRecord
from app.core.workflow_validation import validate_workflow
from app.runtime.agent_state import AgentState
from app.runtime.compiler import compile_workflow


class StepLimitExceededError(Exception):
    """运行超过 max_steps 步数上限（可能含环）。"""


def _derive_main_input(config: AgentConfig, inputs: dict, user_input: str, image_url: str | None) -> tuple[str, str | None]:
    """从命名 inputs 推导主文本输入与图片输入。

    有命名输入时优先用 inputs：主文本取第一个非 image 字段的值，图片取 image 字段的值；
    没有命名输入（或字段未提供）时回退到调用方传入的 user_input / image_url。
    """
    if not inputs:
        return user_input, image_url
    image_names = {f.name for f in config.workflow.inputs if f.type == "image"}
    main = next(
        (str(v) for n, v in inputs.items() if n not in image_names and v not in (None, "")),
        user_input,
    )
    image = next(
        (str(v) for n, v in inputs.items() if n in image_names and v not in (None, "")),
        image_url,
    )
    return main, image or None


async def run_agent(
    agent_config: AgentConfig,
    user_input: str,
    env: str,
    agent_id: str = "",
    version_id: str = "",
    image_url: str | None = None,
    datasources: dict | None = None,
    knowledges: dict | None = None,
    max_steps: int = 100,
    inputs: dict | None = None,
) -> TraceRecord:
    """运行一个 Agent 版本，返回结构化运行记录。

    agent_id / version_id 由上层服务回填；datasources 为 http 节点的数据源配置
    {数据源名: {base_url, method, headers}}；knowledges 为 {知识名: content}（知识注入）。
    二者均由服务层从 DB 解析后传入。

    inputs 为命名输入 {字段名: 值}（按 WorkflowConfig.inputs 收集）；未提供时回退到
    user_input / image_url（兼容单输入调用）。
    """
    inputs = inputs or {}

    # 必填输入校验：清晰中文报错（映射到 400）
    for f in agent_config.workflow.inputs:
        if f.required and not inputs.get(f.name):
            raise ValueError(f"缺少必填输入：{f.label or f.name}")

    # 运行前校验：error 级问题拒绝运行（清晰中文报错而非 LangGraph 裸异常，§9.4）
    errors = [
        i
        for i in validate_workflow(
            agent_config,
            existing_datasources=datasources or {},
            existing_knowledge=set((knowledges or {}).keys()),
        )
        if i.severity == "error"
    ]
    if errors:
        raise ValueError(f"Workflow 校验未通过：{errors[0].message}")

    main_input, resolved_image = _derive_main_input(agent_config, inputs, user_input, image_url)

    graph = compile_workflow(agent_config.workflow)
    initial: AgentState = {
        "input": main_input,
        "inputs": inputs,
        "image_url": resolved_image or "",
        "history": [],
        "vars": {},
        "output": "",
        "trace_steps": [],
        "agent_config": agent_config.model_dump(),
        "datasources": datasources or {},
        "knowledges": knowledges or {},
    }
    try:
        final = await graph.ainvoke(initial, config={"recursion_limit": max_steps})
    except GraphRecursionError as e:
        raise StepLimitExceededError(f"运行超过 {max_steps} 步上限（可能含环），请检查 Workflow") from e
    return TraceRecord(
        trace_id=str(uuid.uuid4()),
        agent_id=agent_id,
        version_id=version_id,
        env=env,
        input=main_input,
        image_url=resolved_image,
        inputs=inputs,
        steps=final["trace_steps"],
        output=final.get("output") or "",
        model=settings.llm_model,
        created_at=datetime.now(UTC).isoformat(),
    )
