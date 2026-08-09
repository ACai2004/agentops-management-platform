"""OptimizationService：反馈 + Trace + 版本 → ModificationPlan → 应用（§10.4，平台核心）。"""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.contracts import AgentConfig, ModelSettings, WorkflowNode
from app.core.llm_schemas import Change, ModificationPlan
from app.core.workflow_validation import validate_workflow
from app.llm.structured import call_structured
from app.models.agent import Agent, AgentVersion
from app.models.feedback import Feedback
from app.models.plan import ModificationPlan as PlanModel
from app.models.trace import Trace
from app.services.agent_service import VERSION_STATUS_DRAFT
from app.services.resources import resource_sets


class OptimizationError(Exception):
    """优化闭环状态冲突。"""


# ---------------------------------------------------------------------------
# ApplyChanges（§8.2）
# ---------------------------------------------------------------------------


def apply_changes(config: AgentConfig, changes: list[Change]) -> AgentConfig:
    """把 changes 应用到配置副本，返回新配置（不改原对象）。"""
    cfg = config.model_copy(deep=True)
    for c in changes:
        if c.target == "prompt" and c.operation == "replace":
            cfg.prompt = c.value or cfg.prompt
        elif c.target == "workflow":
            if c.operation == "add_node":
                node_id = _node_id_from_path(c.path)
                cfg.workflow.steps[node_id] = WorkflowNode.model_validate(c.value)
            elif c.operation == "update_node":
                node_id = _node_id_from_path(c.path)
                node = cfg.workflow.steps[node_id]
                cfg.workflow.steps[node_id] = node.model_copy(update=c.value or {})
            elif c.operation == "remove_node":
                node_id = _node_id_from_path(c.path)
                cfg.workflow.steps.pop(node_id, None)
        elif c.target == "capability_bindings":
            if c.operation == "add" and c.path:
                cfg.capability_bindings[c.path] = c.value
            elif c.operation == "remove" and c.path:
                cfg.capability_bindings.pop(c.path, None)
        elif c.target == "model_settings" and c.operation == "replace":
            cfg.model_settings = ModelSettings.model_validate(c.value)
    return cfg


def _node_id_from_path(path: str | None) -> str:
    if not path:
        raise OptimizationError("Change.path 缺失")
    return path.split(".")[-1]


# ---------------------------------------------------------------------------
# generate_plan
# ---------------------------------------------------------------------------


async def generate_plan(db: Session, feedback_id) -> PlanModel:
    fb = db.get(Feedback, feedback_id)
    if not fb:
        raise OptimizationError(f"反馈 {feedback_id} 不存在")
    trace = db.get(Trace, fb.trace_id)
    if not trace:
        raise OptimizationError("反馈对应的 Trace 不存在")
    agent = db.get(Agent, trace.agent_id)
    if not agent or not agent.current_version_id:
        raise OptimizationError("Agent 无当前发布版本")
    version = db.get(AgentVersion, agent.current_version_id)
    config = AgentConfig.model_validate(
        {
            "prompt": version.prompt,
            "workflow": version.workflow_config,
            "capability_bindings": version.capability_bindings,
            "knowledge_bindings": version.knowledge_bindings,
            "model_settings": version.model_settings,
        }
    )

    system = (
        "你是资深 Agent 优化专家。分析用户反馈与运行 Trace，找出问题与根因，"
        "并给出可被系统直接应用的结构化修改方案。只输出 JSON，不要输出其他内容。\n"
        "输出必须严格符合以下结构：\n"
        '{"problem_analysis": "问题是什么", '
        '"root_cause": "为什么产生", '
        '"suggestions": ["建议一", "建议二"],  '  # 注意：suggestions 必须是字符串数组，用方括号 [ ]
        '"changes": [{"target": "prompt|workflow|model_settings|capability_bindings", '
        '"operation": "replace|add_node|update_node|remove_node|add|remove", '
        '"path": "如 steps.节点名 或 prompt", '
        '"value": 新值, '
        '"description": "给业务人员看的说明"}]}\n'
        "其中 suggestions 必须是一个字符串数组；changes 至少一项；每个 change 的 description 必填。"
    )
    user = (
        f"【Agent 版本配置】\n{config.model_dump_json(indent=2)}\n\n"
        f"【运行 Trace 步骤】\n{_trace_summary(trace)}\n\n"
        f"【业务人员反馈】\n{fb.text}"
    )
    plan = await call_structured(ModificationPlan, system=system, user=user)

    record = PlanModel(
        feedback_id=feedback_id,
        agent_id=agent.id,
        problem_analysis=plan.problem_analysis,
        root_cause=plan.root_cause,
        suggestions=plan.suggestions,
        changes=[c.model_dump() for c in plan.changes],
        status="pending",
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def _trace_summary(trace: Trace) -> str:
    steps = trace.steps or []
    lines = []
    for s in steps[:20]:
        node_id = s.get("node_id", "")
        node_type = s.get("node_type", "")
        output = str(s.get("output", ""))[:200]
        lines.append(f"- {node_id} ({node_type}): {output}")
    return "\n".join(lines) or "（无）"


# ---------------------------------------------------------------------------
# apply_plan / reject_plan
# ---------------------------------------------------------------------------


def apply_plan(db: Session, plan_id, *, approved_by: str = "admin") -> AgentVersion:
    """复制当前版本 → 新 draft → ApplyChanges → 校验（error+warning 拒绝）→ 落库。"""
    plan = db.get(PlanModel, plan_id)
    if not plan:
        raise OptimizationError(f"方案 {plan_id} 不存在")
    if plan.status != "pending":
        raise OptimizationError(f"方案状态为 {plan.status}，只能应用 pending")

    agent = db.get(Agent, plan.agent_id)
    if not agent or not agent.current_version_id:
        raise OptimizationError("Agent 无当前发布版本")
    current = db.get(AgentVersion, agent.current_version_id)

    # 复制当前版本 → 新 draft（先不提交，校验通过再落库）
    next_no = (
        db.scalar(select(func.max(AgentVersion.version_no)).where(AgentVersion.agent_id == agent.id)) or 0
    ) + 1
    draft = AgentVersion(
        agent_id=agent.id,
        version_no=next_no,
        prompt=current.prompt,
        workflow_config=current.workflow_config,
        capability_bindings=current.capability_bindings,
        model_settings=current.model_settings,
        status=VERSION_STATUS_DRAFT,
        created_by=approved_by,
    )
    db.add(draft)
    db.flush()  # 拿到 draft.id

    config = AgentConfig.model_validate(
        {
            "prompt": draft.prompt,
            "workflow": draft.workflow_config,
            "capability_bindings": draft.capability_bindings,
            "knowledge_bindings": draft.knowledge_bindings,
            "model_settings": draft.model_settings,
        }
    )
    new_config = apply_changes(config, [Change.model_validate(c) for c in plan.changes])

    # 校验（含资源存在性）：error + warning 都拒绝（AI 生成候选按发布标准，失败回滚不产生版本）
    ds, kn = resource_sets(db)
    issues = validate_workflow(new_config, existing_datasources=ds, existing_knowledge=kn)
    if issues:
        db.rollback()
        raise OptimizationError(f"应用后校验未通过：{issues[0].message}（{issues[0].code}）")

    draft.prompt = new_config.prompt
    draft.workflow_config = new_config.workflow.model_dump()
    draft.capability_bindings = new_config.capability_bindings
    draft.model_settings = new_config.model_settings.model_dump()
    plan.status = "applied"
    plan.applied_version_id = draft.id
    db.commit()
    db.refresh(draft)
    return draft


def reject_plan(db: Session, plan_id) -> PlanModel:
    plan = db.get(PlanModel, plan_id)
    if not plan:
        raise OptimizationError(f"方案 {plan_id} 不存在")
    plan.status = "rejected"
    db.commit()
    db.refresh(plan)
    return plan
