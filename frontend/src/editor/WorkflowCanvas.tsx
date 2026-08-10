import { useCallback, useEffect, useState } from 'react'
import {
  Background,
  Controls,
  MiniMap,
  ReactFlow,
  addEdge,
  useEdgesState,
  useNodesState,
  type Connection,
  type Edge,
  type Node,
} from '@xyflow/react'
import '@xyflow/react/dist/style.css'
import { Button, Input, Modal, Typography, message } from 'antd'
import { api } from '../api/client'
import type { Datasource, WorkflowConfig } from '../api/client'
import { NODE_META, PALETTE } from './palette'
import { configToGraph, graphToConfig, START_ID } from './serialize'
import NodeConfigPanel from './NodeConfigPanel'
import { nodeTypes } from './nodeTypes'

export default function WorkflowCanvas({
  version,
  readOnly,
  onSaved,
  datasources,
}: {
  version: any
  readOnly: boolean
  onSaved: () => void
  datasources: Datasource[]
}) {
  const [nodes, setNodes, onNodesChange] = useNodesState<Node>([])
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([])
  const [selected, setSelected] = useState<Node | null>(null)
  const [branchModal, setBranchModal] = useState<{ conn?: Connection; edge?: Edge } | null>(null)
  const [branchLabel, setBranchLabel] = useState('')
  const [saving, setSaving] = useState(false)

  // 初始化：根据版本配置加载画布
  useEffect(() => {
    if (!version) return
    const { nodes: ns, edges: es } = configToGraph(version.workflow_config as WorkflowConfig)
    setNodes(ns)
    setEdges(es)
    setSelected(null)
  }, [version?.id])

  const addNode = (type: string) => {
    const id = `${type}_${Math.floor(Math.random() * 10000)}`
    setNodes((ns) => [
      ...ns,
      {
        id,
        type,
        position: { x: 160 + ns.length * 24, y: 100 + ns.length * 24 },
        data: { config: { type, save_as: type === 'end' ? undefined : '' } },
      },
    ])
  }

  // 防呆：拒绝成环、连到开始/从结束连出
  const isValidConnection = useCallback(
    (conn: Connection | Edge) => {
      const c = conn as Connection
      if (!c.source || !c.target || c.source === c.target) return false
      if (c.source === START_ID || c.target === START_ID) return false
      if (nodes.find((n) => n.id === c.source)?.type === 'end') return false
      const q = [c.source]
      const seen = new Set<string>()
      while (q.length) {
        const id = q.shift()!
        if (id === c.target) return false
        if (seen.has(id)) continue
        seen.add(id)
        for (const e of edges) if (e.source === id) q.push(e.target)
      }
      return true
    },
    [nodes, edges],
  )

  const onConnect = useCallback(
    (conn: Connection) => {
      const sourceNode = nodes.find((n) => n.id === conn.source)
      if (sourceNode?.type === 'decision') {
        const n = edges.filter((e) => e.source === conn.source).length + 1
        setBranchLabel(`分支${n}`)
        setBranchModal({ conn })
      } else {
        setEdges((eds) => addEdge({ ...conn, id: `e-${conn.source}-${conn.target}-${Math.random().toString(36).slice(2, 6)}` }, eds))
      }
    },
    [nodes, edges],
  )

  const onEdgeDoubleClick = useCallback((_: React.MouseEvent, edge: Edge) => {
    setBranchLabel(String(edge.label ?? ''))
    setBranchModal({ edge })
  }, [])

  const confirmBranch = () => {
    const modal = branchModal
    if (!modal) return
    if (modal.edge) {
      const edgeId = modal.edge.id
      setEdges((eds) => eds.map((e) => (e.id === edgeId ? { ...e, label: branchLabel } : e)))
    } else if (modal.conn) {
      const conn = modal.conn
      setEdges((eds) => addEdge({ ...conn, id: `e-${conn.source}-${conn.target}-${branchLabel}`, label: branchLabel }, eds))
    }
    setBranchModal(null)
  }

  const save = async () => {
    if (!version) return
    setSaving(true)
    try {
      const cfg = graphToConfig(nodes, edges)
      await api.updateDraft(version.id, { workflow_config: cfg, prompt: version.prompt })
      message.success('已保存')
      onSaved()
    } catch (e: any) {
      message.error(e.response?.data?.message || '保存失败')
    } finally {
      setSaving(false)
    }
  }

  const updateNodeConfig = (cfg: any) => {
    if (!selected) return
    setNodes((ns) => ns.map((n) => (n.id === selected.id ? { ...n, data: { config: cfg } } : n)))
    setSelected((s) => (s ? { ...s, data: { config: cfg } } : s))
  }

  const deleteNode = () => {
    if (!selected) return
    setNodes((ns) => ns.filter((n) => n.id !== selected.id))
    setEdges((es) => es.filter((e) => e.source !== selected.id && e.target !== selected.id))
    setSelected(null)
  }

  return (
    <div
      style={{
        display: 'flex',
        height: 560,
        border: '1px solid #f0f0f0',
        borderRadius: 8,
        overflow: 'hidden',
        background: '#fff',
      }}
    >
      <div style={{ width: 150, borderRight: '1px solid #f0f0f0', padding: 8 }}>
        <Typography.Text type="secondary" style={{ fontSize: 12 }}>
          节点库
        </Typography.Text>
        {PALETTE.map((p) => (
          <Button
            key={p.type}
            block
            disabled={readOnly}
            style={{ marginTop: 8, color: NODE_META[p.type].color, borderColor: NODE_META[p.type].color, background: NODE_META[p.type].bg }}
            onClick={() => addNode(p.type)}
          >
            + {p.label}
          </Button>
        ))}
        <Button type="primary" block style={{ marginTop: 20 }} loading={saving} disabled={readOnly} onClick={save}>
          保存
        </Button>
      </div>

      <div style={{ flex: 1, position: 'relative' }}>
        <ReactFlow
          nodes={nodes}
          edges={edges}
          nodeTypes={nodeTypes}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          isValidConnection={isValidConnection}
          onConnect={onConnect}
          onNodeClick={(_, n) => setSelected(n)}
          onPaneClick={() => setSelected(null)}
          onEdgeDoubleClick={onEdgeDoubleClick}
          fitView
          nodesDraggable={!readOnly}
          nodesConnectable={!readOnly}
          proOptions={{ hideAttribution: true }}
        >
          <Background />
          <Controls />
          <MiniMap pannable zoomable />
        </ReactFlow>
        {readOnly && (
          <div
            style={{
              position: 'absolute',
              top: 8,
              left: '50%',
              transform: 'translateX(-50%)',
              background: '#fffbe6',
              padding: '4px 12px',
              borderRadius: 6,
              fontSize: 12,
            }}
          >
            线上版本（只读，新建草稿后可编辑）
          </div>
        )}
      </div>

      <div style={{ width: 260, borderLeft: '1px solid #f0f0f0', padding: 8, overflow: 'auto' }}>
        <NodeConfigPanel
          node={selected}
          onChange={updateNodeConfig}
          onDelete={deleteNode}
          datasources={datasources}
        />
      </div>

      <Modal
        title="分支值"
        open={!!branchModal}
        onOk={confirmBranch}
        onCancel={() => setBranchModal(null)}
        width={320}
      >
        <Input
          value={branchLabel}
          onChange={(e) => setBranchLabel(e.target.value)}
          placeholder="分支值，如 satisfied"
        />
        <Typography.Text type="secondary" style={{ fontSize: 12 }}>
          分支值会显示在连线上，判断分支按此值路由。
        </Typography.Text>
      </Modal>
    </div>
  )
}
