import { Handle, Position, type NodeProps } from '@xyflow/react'
import { NODE_META } from './palette'

// 步骤节点：圆角卡片 + 颜色 + 友好名 + 左右接口
export function StepNode({ type, selected, data }: NodeProps) {
  const meta = NODE_META[type as string] || NODE_META.llm
  const cfg: any = data?.config || {}
  return (
    <div
      style={{
        border: `2px solid ${selected ? '#1677ff' : meta.color}`,
        background: meta.bg,
        borderRadius: 8,
        padding: '8px 14px',
        minWidth: 130,
        textAlign: 'center',
        fontSize: 13,
        boxShadow: '0 1px 3px rgba(0,0,0,0.08)',
      }}
    >
      {type !== 'start' && <Handle type="target" position={Position.Left} />}
      <div style={{ fontWeight: 600, color: meta.color }}>{meta.label}</div>
      {cfg.save_as && <div style={{ color: '#888', fontSize: 11 }}>{cfg.save_as}</div>}
      {type === 'http' && cfg.datasource && (
        <div style={{ color: '#52c41a', fontSize: 11 }}>{cfg.datasource}</div>
      )}
      {type !== 'end' && <Handle type="source" position={Position.Right} />}
    </div>
  )
}

export const nodeTypes = {
  llm: StepNode,
  decision: StepNode,
  http: StepNode,
  end: StepNode,
  start: StepNode,
}
