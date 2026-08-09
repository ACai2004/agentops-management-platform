"""Layer 3 验收：编译器把 WorkflowConfig 正确翻译成 LangGraph 图。

断言图节点数 + 边结构。注意：langgraph 1.x 未暴露稳定的"边数"公共 API
（compiled.edges 不存在，get_graph() 的可视化边不展开条件分支），
因此这里用「config 引用的每个目标都可达 + 每个节点都有入边触发 + 入口边存在」
来等价验证边结构的正确性。
"""

from app.core.contracts import AgentConfig, WorkflowConfig
from app.runtime.compiler import compile_workflow
from tests.sample_data import SAMPLE_WORKFLOW


def _compiled():
    cfg = AgentConfig(
        prompt="你是餐后体验回访助手",
        workflow=WorkflowConfig.model_validate(SAMPLE_WORKFLOW),
    )
    return compile_workflow(cfg.workflow)


def test_node_count_matches_steps():
    """图节点数 = workflow 节点数 + __start__ 入口节点。"""
    compiled = _compiled()
    workflow_nodes = {k for k in compiled.nodes if not k.startswith("__")}
    assert workflow_nodes == set(SAMPLE_WORKFLOW["steps"])
    assert len(workflow_nodes) == len(SAMPLE_WORKFLOW["steps"]) == 5
    assert "__start__" in compiled.nodes


def test_all_referenced_destinations_connected():
    """config 中 next / branches 引用的每个目标节点都存在于图中（边可达性）。"""
    compiled = _compiled()
    node_ids = set(compiled.nodes)
    for node_id, node in SAMPLE_WORKFLOW["steps"].items():
        if node.get("next"):
            assert node["next"] in node_ids, f"{node_id}.next -> {node['next']} 不在图中"
        for dest in (node.get("branches") or {}).values():
            assert dest in node_ids, f"{node_id}.branches -> {dest} 不在图中"


def test_start_edge_and_incoming_triggers():
    """入口边存在，且每个 workflow 节点都有入边触发（图是连通的）。"""
    compiled = _compiled()
    vg = compiled.get_graph()
    start_edges = [e for e in vg.edges if e.source == "__start__"]
    assert any(e.target == SAMPLE_WORKFLOW["start"] for e in start_edges)

    triggers = [k for k in compiled.trigger_to_nodes if k.startswith("branch:to:")]
    assert len(triggers) == len(SAMPLE_WORKFLOW["steps"])  # 每个节点对应一条入边触发
