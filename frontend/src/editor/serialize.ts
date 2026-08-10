import type { Edge, Node } from '@xyflow/react'
import type { WorkflowConfig, WorkflowNode } from '../api/client'

export const START_ID = '__start__'

// 画布 → WorkflowConfig（保存时用）
export function graphToConfig(nodes: Node[], edges: Edge[]): WorkflowConfig {
  const stepNodes = nodes.filter((n) => n.id !== START_ID)
  const incoming = new Set(edges.map((e) => e.target))
  const startEdge = edges.find((e) => e.source === START_ID)
  const start =
    startEdge?.target || stepNodes.find((n) => !incoming.has(n.id))?.id || stepNodes[0]?.id || 'end'

  const steps: Record<string, WorkflowNode> = {}
  for (const n of stepNodes) {
    const cfg = (n.data?.config ?? { type: 'llm' }) as WorkflowNode
    const out = edges.filter((e) => e.source === n.id)
    const base: WorkflowNode = {
      type: (cfg.type as WorkflowNode['type']) || 'llm',
      prompt: cfg.prompt ?? '',
      save_as: cfg.save_as ?? '',
      ...(cfg.model_settings ? { model_settings: cfg.model_settings } : {}),
      ...(cfg.image_input ? { image_input: true } : {}),
    }
    if (base.type === 'decision') {
      base.branches = {}
      for (const e of out) {
        const label = String(e.label ?? '')
        if (label) base.branches[label] = e.target
      }
    } else if (base.type === 'http') {
      base.datasource = cfg.datasource ?? ''
      base.params = cfg.params ?? {}
      base.next = out[0]?.target ?? null
    } else if (base.type === 'llm') {
      base.next = out[0]?.target ?? null
    }
    steps[n.id] = base
  }
  if (!steps['end']) steps['end'] = { type: 'end' }
  return { start, steps }
}

// WorkflowConfig → 画布（加载时用，BFS 布局）
export function configToGraph(cfg: WorkflowConfig): { nodes: Node[]; edges: Edge[] } {
  const steps = cfg.steps || {}
  const positions: Record<string, { x: number; y: number }> = {}
  const depth: Record<string, number> = {}
  const order: string[] = []
  const seen = new Set<string>()
  if (cfg.start in steps) {
    depth[cfg.start] = 0
    seen.add(cfg.start)
    const queue = [cfg.start]
    while (queue.length) {
      const id = queue.shift()!
      order.push(id)
      const node = steps[id]
      const deps = node.type === 'decision' ? Object.values(node.branches || {}) : node.next ? [node.next] : []
      for (const t of deps) {
        if (t && t in steps && !seen.has(t)) {
          seen.add(t)
          depth[t] = (depth[id] ?? 0) + 1
          queue.push(t)
        }
      }
    }
  }
  // 未覆盖到的节点（孤立）也摆出来
  for (const id of Object.keys(steps)) {
    if (!seen.has(id)) {
      depth[id] = 0
      seen.add(id)
      order.push(id)
    }
  }
  const depthIndex: Record<number, number> = {}
  for (const id of order) {
    const d = depth[id] ?? 0
    depthIndex[d] = (depthIndex[d] ?? 0) + 1
    positions[id] = { x: d * 250, y: (depthIndex[d] - 1) * 140 }
  }

  const nodes: Node[] = [
    { id: START_ID, type: 'start', position: { x: -50, y: 60 }, data: {} },
  ]
  for (const [id, node] of Object.entries(steps)) {
    nodes.push({ id, type: node.type, position: positions[id] ?? { x: 0, y: 0 }, data: { config: node } })
  }

  const edges: Edge[] = []
  if (cfg.start && cfg.start in steps) {
    edges.push({ id: `e-${START_ID}-${cfg.start}`, source: START_ID, target: cfg.start })
  }
  for (const [id, node] of Object.entries(steps)) {
    if (node.type === 'decision') {
      for (const [k, t] of Object.entries(node.branches || {})) {
        edges.push({ id: `e-${id}-${t}-${k}`, source: id, target: t, label: k })
      }
    } else if (node.next) {
      edges.push({ id: `e-${id}-${node.next}`, source: id, target: node.next })
    }
  }
  return { nodes, edges }
}
