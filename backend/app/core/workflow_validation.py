"""四层校验（蓝图 §3 / 《AgentOps工作流校验与运行时设计.md》）。

collect-all：一次返回全部问题，不 fail-fast；由调用方决定哪些严重度阻断。
纯函数：只依赖 AgentConfig（+ 可选的数据源名集合），不触碰 DB。
"""

from collections import deque
from typing import Literal

from pydantic import BaseModel

from app.core.contracts import AgentConfig, WorkflowConfig
from app.core.model_registry import model_supports


class WorkflowIssue(BaseModel):
    node_id: str | None = None            # 定位到哪个节点（None = 全局问题）
    code: str                             # 如 "CYCLE" / "UNREACHABLE_NODE"
    severity: Literal["error", "warning"]
    message: str                          # 业务人员能看懂的中文描述


def validate_workflow(
    config: AgentConfig,
    existing_datasources: set[str] | None = None,
    existing_knowledge: set[str] | None = None,
) -> list[WorkflowIssue]:
    """校验整个 AgentConfig（含 workflow + 模型设置），返回全部问题。

    existing_datasources / existing_knowledge：已有资源名集合；为 None 时跳过对应检查
    （由服务层从 DB 传入）。
    """
    issues: list[WorkflowIssue] = []
    workflow: WorkflowConfig = config.workflow
    steps = workflow.steps

    # ---------------- Layer 3A · 知识绑定 ----------------
    if existing_knowledge is not None:
        for name in config.knowledge_bindings:
            if name not in existing_knowledge:
                issues.append(_issue(None, "KNOWLEDGE_BINDING_MISSING", "error", f"绑定的知识 {name} 不存在"))

    # ---------------- Layer 2 · Topology ----------------
    if workflow.start not in steps:
        issues.append(_issue(None, "MISSING_START", "error", f"起始节点 {workflow.start} 不存在"))

    for nid, node in steps.items():
        if node.type in ("llm", "http") and node.next and node.next not in steps:
            issues.append(_issue(nid, "DANGLING_EDGE", "error", f"next 指向不存在的节点 {node.next}"))
        if node.type == "decision" and node.branches:
            for k, dest in node.branches.items():
                if dest not in steps:
                    issues.append(_issue(nid, "DANGLING_EDGE", "error", f"分支 {k} 指向不存在的节点 {dest}"))

    if not any(n.type == "end" for n in steps.values()):
        issues.append(_issue(None, "MISSING_END", "error", "缺少 end 节点"))

    if workflow.start in steps:
        cycle = _find_cycle(steps, workflow.start)
        if cycle:
            issues.append(_issue(None, "CYCLE", "error", f"检测到环路：{' → '.join(cycle)}"))
        for nid in _find_unreachable(steps, workflow.start):
            issues.append(_issue(nid, "UNREACHABLE_NODE", "warning", "节点从 start 不可达"))

    # ---------------- Layer 3A · Semantic 节点字段 ----------------
    for nid, node in steps.items():
        if node.type in ("llm", "decision"):
            if not (node.prompt and node.prompt.strip()):
                issues.append(_issue(nid, "MISSING_PROMPT", "error", "缺少 prompt"))
            if not node.save_as:
                if node.type == "decision":
                    issues.append(_issue(nid, "MISSING_SAVE_AS", "error", "decision 必须有 save_as（否则路由恒坏）"))
                else:
                    issues.append(_issue(nid, "MISSING_SAVE_AS", "warning", "llm 应有 save_as（否则输出丢失）"))
        if node.type == "decision":
            if not node.branches:
                issues.append(_issue(nid, "EMPTY_BRANCHES", "error", "decision 必须配置 branches"))
            if node.next:
                issues.append(_issue(nid, "DECISION_HAS_NEXT", "warning", "decision 不使用 next（已忽略）"))
        if node.type == "llm":
            if not node.next:
                issues.append(_issue(nid, "LLM_MISSING_NEXT", "warning", "llm 必须有 next"))
            if node.branches:
                issues.append(_issue(nid, "LLM_HAS_BRANCHES", "warning", "llm 不使用 branches（已忽略）"))
        if node.type == "end" and (node.next or node.branches):
            issues.append(_issue(nid, "END_HAS_NEXT", "warning", "end 不应有 next/branches（已忽略）"))
        if node.type == "http":
            if existing_datasources is not None and node.datasource not in existing_datasources:
                issues.append(_issue(nid, "DATASOURCE_MISSING", "error", f"数据源 {node.datasource} 不存在"))
            if not node.save_as:
                issues.append(_issue(nid, "HTTP_MISSING_SAVE_AS", "error", "http 必须有 save_as"))
            if not node.next:
                issues.append(_issue(nid, "HTTP_MISSING_NEXT", "warning", "http 必须有 next"))
            if node.branches:
                issues.append(_issue(nid, "HTTP_HAS_BRANCHES", "warning", "http 不使用 branches（已忽略）"))

    # ---------------- Layer 3B · 模型能力 ----------------
    for nid, node in steps.items():
        if node.type == "llm" and node.image_input:
            model = _resolve_node_model(node, config)
            if not model_supports(model, ["vision"]):
                issues.append(
                    _issue(
                        nid,
                        "MODEL_CAPABILITY_MISMATCH",
                        "error",
                        f"节点使用图片输入，但模型 {model} 不支持视觉",
                    )
                )

    return issues


def _issue(node_id, code, severity, message) -> WorkflowIssue:
    return WorkflowIssue(node_id=node_id, code=code, severity=severity, message=message)


def _resolve_node_model(node, config: AgentConfig) -> str:
    if node.model_settings is not None and node.model_settings.model:
        return node.model_settings.model
    return config.model_settings.model


def _next_targets(steps, nid: str) -> list[str]:
    """按节点类型返回出边目标（不含 END）。"""
    node = steps[nid]
    if node.type in ("llm", "http"):
        return [node.next] if node.next else []
    if node.type == "decision":
        return list((node.branches or {}).values())
    return []


def _find_unreachable(steps, start: str) -> list[str]:
    """BFS：返回从 start 不可达的节点 id 列表。"""
    reachable: set[str] = set()
    q: deque[str] = deque([start])
    while q:
        nid = q.popleft()
        if nid in reachable or nid not in steps:
            continue
        reachable.add(nid)
        for t in _next_targets(steps, nid):
            if t in steps and t not in reachable:
                q.append(t)
    return [nid for nid in steps if nid not in reachable]


def _find_cycle(steps, start: str) -> list[str]:
    """DFS 三色法：返回一个环的节点序列（含回到起点），无环返回 []。"""
    WHITE, GRAY, BLACK = 0, 1, 2
    color = {nid: WHITE for nid in steps}
    stack: list[str] = []

    def dfs(nid: str):
        color[nid] = GRAY
        stack.append(nid)
        for t in _next_targets(steps, nid):
            if t not in steps:
                continue
            if color[t] == GRAY:
                i = stack.index(t)
                return stack[i:] + [t]
            if color[t] == WHITE:
                res = dfs(t)
                if res:
                    return res
        stack.pop()
        color[nid] = BLACK
        return None

    if start not in steps:
        return []
    return dfs(start) or []
