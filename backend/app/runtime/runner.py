"""运行入口（§9.4）：编译图 + 执行 + 产出 TraceRecord。"""

import uuid
from datetime import UTC, datetime

from app.core.config import settings
from app.core.contracts import AgentConfig, TraceRecord
from app.runtime.agent_state import AgentState
from app.runtime.compiler import compile_workflow


async def run_agent(
    agent_config: AgentConfig,
    user_input: str,
    env: str,
    agent_id: str = "",
    version_id: str = "",
) -> TraceRecord:
    """运行一个 Agent 版本，返回结构化运行记录。

    agent_id / version_id 由上层服务回填（Layer 4 起）；本层不感知具体 Agent。
    """
    graph = compile_workflow(agent_config.workflow)
    initial: AgentState = {
        "input": user_input,
        "history": [],
        "vars": {},
        "output": "",
        "trace_steps": [],
        "agent_config": agent_config.model_dump(),
    }
    final = await graph.ainvoke(initial)
    return TraceRecord(
        trace_id=str(uuid.uuid4()),
        agent_id=agent_id,
        version_id=version_id,
        env=env,
        input=user_input,
        steps=final["trace_steps"],
        output=final.get("output") or "",
        model=settings.llm_model,
        created_at=datetime.now(UTC).isoformat(),
    )
