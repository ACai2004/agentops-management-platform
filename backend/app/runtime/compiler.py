"""WorkflowConfig -> LangGraph StateGraph 的编译器（§9.2）。

编译层是唯一接触 LangGraph 的地方；业务代码不得 import langgraph。
"""

from langgraph.graph import END, START, StateGraph

from app.core.contracts import WorkflowConfig, WorkflowNode
from app.runtime.agent_state import AgentState
from app.runtime.nodes import (
    make_decision_node,
    make_end_node,
    make_http_node,
    make_llm_node,
    make_template_node,
)


def _fallback_destination(steps: dict[str, WorkflowNode]):
    """decision 路由找不到合法分支时的兜底：优先走到 end 节点，否则直接 END。"""
    for node_id, node in steps.items():
        if node.type == "end":
            return node_id
    return END


def make_router(node: WorkflowNode, fallback_dest):
    """decision 节点的路由函数：按 choice 在 branches 里选下一个节点，否则兜底。"""
    branches = node.branches or {}

    def route(state):
        choice = state["vars"].get(node.save_as, {}).get("choice")
        return branches.get(choice, fallback_dest)

    return route


def compile_workflow(config: WorkflowConfig):
    """把 WorkflowConfig 编译为可运行的 CompiledGraph。"""
    g = StateGraph(AgentState)

    # 1) 注册节点
    for node_id, node in config.steps.items():
        if node.type == "llm":
            g.add_node(node_id, make_llm_node(node_id, node))
        elif node.type == "decision":
            g.add_node(node_id, make_decision_node(node_id, node))
        elif node.type == "http":
            g.add_node(node_id, make_http_node(node_id, node))
        elif node.type == "template":
            g.add_node(node_id, make_template_node(node_id, node))
        elif node.type == "end":
            g.add_node(node_id, make_end_node(node_id))

    fallback_dest = _fallback_destination(config.steps)

    # 2) 连边
    for node_id, node in config.steps.items():
        if node.type in ("llm", "http", "template") and node.next:
            g.add_edge(node_id, node.next)
        elif node.type == "decision":
            # route 直接返回目标节点名（或 END），不需要 path_map
            g.add_conditional_edges(node_id, make_router(node, fallback_dest))
        elif node.type == "end":
            g.add_edge(node_id, END)

    g.add_edge(START, config.start)
    return g.compile()
