import { createContext, useContext } from 'react'
import { BaseEdge, EdgeLabelRenderer, getBezierPath, type EdgeProps } from '@xyflow/react'
import { Button } from 'antd'
import { DeleteOutlined, EditOutlined } from '@ant-design/icons'

export interface EdgeActions {
  onDeleteEdge?: (id: string) => void
  onEditEdge?: (id: string) => void
}

/** 供自定义连线组件读取"删除 / 改分支值"的回调（由 WorkflowCanvas 提供）。 */
export const EdgeActionsContext = createContext<EdgeActions>({})

/**
 * 自定义连线：点选一条线后，在线的中点附近浮出 删除 / 改分支值 按钮（Canva 式）。
 * 分支值（label）也在这里渲染，样式可控。
 */
export default function FlowEdge(props: EdgeProps) {
  const {
    id,
    sourceX,
    sourceY,
    targetX,
    targetY,
    sourcePosition,
    targetPosition,
    selected,
    label,
    markerEnd,
    style,
  } = props
  const { onDeleteEdge, onEditEdge } = useContext(EdgeActionsContext)
  const [path, labelX, labelY] = getBezierPath({ sourceX, sourceY, targetX, targetY, sourcePosition, targetPosition })

  return (
    <>
      <BaseEdge id={id} path={path} markerEnd={markerEnd} style={style} />

      {/* 分支值标签（如 退货/咨询/投诉） */}
      {label != null && (
        <EdgeLabelRenderer>
          <div
            className="nodrag nopan"
            style={{
              position: 'absolute',
              transform: `translate(-50%, -50%) translate(${labelX}px, ${labelY}px)`,
              pointerEvents: 'all',
              background: '#fff',
              border: '1px solid #d9d9d9',
              borderRadius: 4,
              padding: '0 5px',
              fontSize: 11,
              zIndex: 10,
            }}
          >
            {String(label)}
          </div>
        </EdgeLabelRenderer>
      )}

      {/* 选中后浮出的操作按钮 */}
      {selected && (
        <EdgeLabelRenderer>
          <div
            className="nodrag nopan"
            style={{
              position: 'absolute',
              transform: `translate(-50%, -50%) translate(${labelX}px, ${labelY - 16}px)`,
              pointerEvents: 'all',
              display: 'flex',
              gap: 2,
              zIndex: 20,
            }}
          >
            <Button
              size="small"
              type="text"
              danger
              icon={<DeleteOutlined />}
              style={{ background: '#fff', boxShadow: '0 1px 3px rgba(0,0,0,0.2)' }}
              onClick={() => onDeleteEdge?.(id)}
            />
            {label != null && (
              <Button
                size="small"
                type="text"
                icon={<EditOutlined />}
                style={{ background: '#fff', boxShadow: '0 1px 3px rgba(0,0,0,0.2)' }}
                onClick={() => onEditEdge?.(id)}
              />
            )}
          </div>
        </EdgeLabelRenderer>
      )}
    </>
  )
}
