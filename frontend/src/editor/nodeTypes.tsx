import { Handle, Position, type NodeProps } from '@xyflow/react'
import { NODE_META } from './palette'

// 步骤节点：圆角卡片 + 颜色 + 友好名 + 左右接口
export function StepNode({ type, selected, data }: NodeProps) {
  const meta = NODE_META[type as string] || NODE_META.llm
  const cfg: any = data?.config || {}
  const inputs: any[] = (data?.inputs as any[]) || []
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
      {type === 'start' && (
        <>
          {inputs.length === 0 ? (
            <div style={{ color: '#888', fontSize: 11 }}>未配置输入</div>
          ) : (
            inputs.map((f, i) => (
              <div key={i} style={{ color: '#888', fontSize: 11, textAlign: 'left' }}>
                {f.required ? '必填 ' : ''}
                {f.label || f.name}（{f.type}）
              </div>
            ))
          )}
          <div style={{ color: '#bbb', fontSize: 10, marginTop: 2 }}>→ 拖到第一步设为起点</div>
        </>
      )}
      {type !== 'start' && cfg.save_as && <div style={{ color: '#888', fontSize: 11 }}>{cfg.save_as}</div>}
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
  template: StepNode,
  end: StepNode,
  start: StepNode,
}
