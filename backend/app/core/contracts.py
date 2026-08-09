"""管理层与运行时之间的两个核心契约。

- AgentConfig：Agent 版本快照（Prompt + Workflow + 能力绑定 + 模型设置）
- TraceRecord：结构化运行记录（对齐 OpenInference 语义，为将来导出预留）

设计原则：业务代码只依赖这两个契约，不直接 import LangGraph。
"""

from typing import Any, Literal

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# §5.1 AgentConfig
# ---------------------------------------------------------------------------


class ModelSettings(BaseModel):
    model: str = "deepseek/deepseek-v4-flash"
    temperature: float = 0.7
    max_tokens: int = 1024


class WorkflowNode(BaseModel):
    type: Literal["llm", "decision", "end"]
    prompt: str | None = None            # llm/decision 必填
    save_as: str | None = None           # llm/decision 必填（写入 AgentState.vars 的 key）
    next: str | None = None              # llm 节点：下一节点 id
    branches: dict[str, str] | None = None  # decision 节点：{分支值: 下一节点 id}
    model_settings: ModelSettings | None = None  # 节点级覆盖（可选）


class WorkflowConfig(BaseModel):
    start: str                           # 起始节点 id
    steps: dict[str, WorkflowNode]       # 节点 id -> 定义


class AgentConfig(BaseModel):
    prompt: str                          # Agent 系统提示词
    workflow: WorkflowConfig
    capability_bindings: dict[str, Any] = Field(default_factory=dict)  # {能力名: 绑定参数}
    model_settings: ModelSettings = Field(default_factory=ModelSettings)


# ---------------------------------------------------------------------------
# §5.2 Trace
# ---------------------------------------------------------------------------


class TraceStep(BaseModel):
    node_id: str
    node_type: Literal["llm", "decision", "end"]
    input: str | None = None             # 本节点的输入（透传相关上下文）
    output: str | dict | None = None     # LLM 返回 / decision 判断
    branch: str | None = None            # decision 选中的分支
    model: str | None = None
    prompt: str | None = None            # 实际使用的 prompt（含系统注入）
    token_usage: dict[str, int] | None = None  # {prompt_tokens, completion_tokens, total_tokens}
    latency_ms: float | None = None


class TraceRecord(BaseModel):
    trace_id: str
    agent_id: str
    version_id: str
    env: Literal["test", "live"]
    input: str
    steps: list[TraceStep]
    output: str
    model: str
    created_at: str   # ISO8601
