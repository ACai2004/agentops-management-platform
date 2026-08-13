import { useCallback, useEffect, useMemo, useState } from 'react'
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
import { NodeIndexOutlined } from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import { api } from '../api/client'
import type { Datasource, InputField, WorkflowConfig } from '../api/client'
import FlowEdge, { EdgeActionsContext } from './FlowEdge'
import { NODE_META, PALETTE } from './palette'
import { configToGraph, graphToConfig, START_ID } from './serialize'
import NodeConfigPanel from './NodeConfigPanel'
import { nodeTypes } from './nodeTypes'

// 连线组件：点选后浮出 删除/改分支值 按钮
const flowEdgeTypes = { default: FlowEdge }

export default function WorkflowCanvas({
  version,
  readOnly,
  onSaved,
  datasources,
  agentId,
}: {
  version: any
  readOnly: boolean
  onSaved: () => void
  datasources: Datasource[]
  agentId: string
}) {
  const [nodes, setNodes, onNodesChange] = useNodesState<Node>([])
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([])
  const [selected, setSelected] = useState<Node | null>(null)
  const [drawMode, setDrawMode] = useState(false)
  const [drawSource, setDrawSource] = useState<string | null>(null)
  const [branchModal, setBranchModal] = useState<{ conn?: Connection; edge?: Edge } | null>(null)
  const [branchLabel, setBranchLabel] = useState('')
  const [saving, setSaving] = useState(false)
  const navigate = useNavigate()

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

  // 防呆：拒绝成环、连到开始/从结束连出；开始节点可手动连线指定起点（替换旧起点）
  const isValidConnection = useCallback(
    (conn: Connection | Edge) => {
      const c = conn as Connection
      if (!c.source || !c.target || c.source === c.target) return false
      if (c.target === START_ID) return false                 // 不能连进开始
      if (c.source === START_ID) return true                  // 从开始拉线：允许（onConnect 里替换旧起点线）
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

  const createConnection = useCallback(
    (conn: Connection) => {
      if (conn.source === START_ID) {
        // 从开始节点拉线：替换已有的开始连线（起点只能有一个），并清掉旧连线
        setEdges((eds) => [
          ...eds.filter((e) => e.source !== START_ID),
          { ...conn, id: `e-${START_ID}-${conn.target}` },
        ])
        return
      }
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

  // 画线模式：点第一个节点设起点，点第二个节点连线（判断分支会弹框设分支值）
  const handleNodeClick = useCallback(
    (_e: any, n: Node) => {
      if (!drawMode) {
        setSelected(n)
        return
      }
      if (!drawSource) {
        setDrawSource(n.id)
        return
      }
      if (drawSource === n.id) {
        setDrawSource(null) // 再点一次取消起点
        return
      }
      const conn: Connection = { source: drawSource, target: n.id, sourceHandle: null, targetHandle: null }
      if (isValidConnection(conn)) {
        createConnection(conn)
        const srcType = nodes.find((x) => x.id === drawSource)?.type
        if (srcType === 'decision') {
          setDrawSource(null) // 判断分支：画完一条继续点下一个分支目标
        } else {
          setDrawMode(false)
          setDrawSource(null)
        }
      }
    },
    [drawMode, drawSource, nodes, isValidConnection, createConnection],
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
      // 只保存工作流；系统提示词由 WorkflowTab 的独立按钮保存，避免互相覆盖
      await api.updateDraft(version.id, { workflow_config: cfg })
      message.success('已保存')
      onSaved()
    } catch (e: any) {
      message.error(e.response?.data?.message || '保存失败')
    } finally {
      setSaving(false)
    }
  }

  const updateNodeConfig = (data: any) => {
    if (!selected) return
    setNodes((ns) => ns.map((n) => (n.id === selected.id ? { ...n, data } : n)))
    setSelected((s) => (s ? { ...s, data } : s))
  }

  // 删除 Agent：软删除（历史数据保留），确认后返回列表
  const confirmDeleteAgent = () => {
    Modal.confirm({
      title: '确认要删除此工作流吗？',
      content: '删除后历史数据保留，仅从列表隐藏（可恢复）。',
      okText: '删除',
      okButtonProps: { danger: true },
      cancelText: '取消',
      onOk: async () => {
        try {
          await api.deleteAgent(agentId)
          message.success('已删除')
          navigate('/')
        } catch (e: any) {
          message.error(e.response?.data?.message || '删除失败')
        }
      },
    })
  }

  const deleteNode = () => {
    if (!selected) return
    setNodes((ns) => ns.filter((n) => n.id !== selected.id))
    setEdges((es) => es.filter((e) => e.source !== selected.id && e.target !== selected.id))
    setSelected(null)
  }

  // 选中节点"可用的输入"：上游可达节点的产物变量 + 工作流输入 + 绑定知识 + 静态提示词
  const nodeInputs = useMemo(() => {
    if (!selected) return null
    const reach = new Set<string>()
    const queue = [selected.id]
    while (queue.length) {
      const id = queue.shift()!
      for (const e of edges) {
        if (e.target === id && !reach.has(e.source)) {
          reach.add(e.source)
          queue.push(e.source)
        }
      }
    }
    const vars = nodes
      .filter((n) => reach.has(n.id) && n.id !== START_ID)
      .map((n) => ({
        nodeId: n.id,
        saveAs: (n.data?.config as any)?.save_as as string | undefined,
        type: n.type as string,
      }))
      .filter((v) => v.saveAs)
    const inputs = (nodes.find((n) => n.id === START_ID)?.data?.inputs as InputField[] | undefined) || []
    return {
      vars,
      inputs,
      knowledge: (version?.knowledge_bindings as string[] | undefined) || [],
      hasAgentPrompt: !!(version?.prompt && version.prompt.trim()),
    }
  }, [selected, nodes, edges, version])

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
        <Button danger block style={{ marginTop: 8 }} onClick={confirmDeleteAgent}>
          删除 Agent
        </Button>
      </div>

      <div style={{ flex: 1, position: 'relative' }}>
        <EdgeActionsContext.Provider
          value={{
            onDeleteEdge: (id: string) => setEdges((eds) => eds.filter((e) => e.id !== id)),
            onEditEdge: (id: string) => {
              const edge = edges.find((e) => e.id === id)
              if (edge) {
                setBranchLabel(String(edge.label ?? ''))
                setBranchModal({ edge })
              }
            },
          }}
        >
          <ReactFlow
            nodes={nodes}
            edges={edges}
            nodeTypes={nodeTypes}
            edgeTypes={flowEdgeTypes}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            isValidConnection={isValidConnection}
            onConnect={createConnection}
            onNodeClick={handleNodeClick}
            onPaneClick={() => {
              setSelected(null)
              if (drawMode) setDrawSource(null)
            }}
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
        </EdgeActionsContext.Provider>

        {/* 画线工具条 */}
        {!readOnly && (
          <div
            style={{
              position: 'absolute',
              top: 8,
              left: 8,
              zIndex: 30,
              display: 'flex',
              alignItems: 'center',
              gap: 8,
              background: '#fff',
              border: '1px solid #f0f0f0',
              borderRadius: 6,
              padding: '4px 8px',
              boxShadow: '0 1px 3px rgba(0,0,0,0.08)',
            }}
          >
            <Button
              size="small"
              type={drawMode ? 'primary' : 'default'}
              icon={<NodeIndexOutlined />}
              onClick={() => {
                setDrawMode((m) => !m)
                setDrawSource(null)
              }}
            >
              {drawMode ? '退出画线' : '画线'}
            </Button>
            {drawMode && (
              <Typography.Text style={{ fontSize: 12, color: '#666' }}>
                {drawSource ? `已选起点 ${drawSource}，点目标节点连线` : '点一个节点作为起点'}
              </Typography.Text>
            )}
          </div>
        )}

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
          nodeInputs={nodeInputs}
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
