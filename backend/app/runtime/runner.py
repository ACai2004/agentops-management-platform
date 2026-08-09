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
) -> TraceRecord:
    """运行一个 Agent 版本，返回结构化运行记录。

    agent_id / version_id 由上层服务回填；datasources 为 http 节点的数据源配置
    {数据源名: {base_url, method, headers}}；knowledges 为 {知识名: content}（知识注入）。
    二者均由服务层从 DB 解析后传入。
    """
    # 运行前校验：error 级问题拒绝运行（清晰中文报错而非 LangGraph 裸异常，§9.4）
    errors = [
        i
        for i in validate_workflow(
            agent_config,
            existing_datasources=set((datasources or {}).keys()),
            existing_knowledge=set((knowledges or {}).keys()),
        )
        if i.severity == "error"
    ]
    if errors:
        raise ValueError(f"Workflow 校验未通过：{errors[0].message}")

    graph = compile_workflow(agent_config.workflow)
    initial: AgentState = {
        "input": user_input,
        "image_url": image_url or "",
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
        input=user_input,
        image_url=image_url,
        steps=final["trace_steps"],
        output=final.get("output") or "",
        model=settings.llm_model,
        created_at=datetime.now(UTC).isoformat(),
    )
