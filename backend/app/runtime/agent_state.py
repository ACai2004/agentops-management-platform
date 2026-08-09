"""LangGraph 运行时状态定义（§9.1）。

AgentState 是图节点之间传递的状态；业务代码不直接接触 LangGraph。
"""

from typing import TypedDict


class AgentState(TypedDict):
    input: str                     # 用户输入
    history: list[str]             # 对话历史（MVP 简化为最近 N 轮）
    vars: dict                     # 节点产物：{save_as: value}
    output: str                    # 最终输出
    trace_steps: list              # list[TraceStep]（dict 形式，便于序列化）
    agent_config: dict             # 原始 AgentConfig（供节点读取）
