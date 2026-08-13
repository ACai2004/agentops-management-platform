import { Button, Popover, Typography } from 'antd'
import { FunctionOutlined } from '@ant-design/icons'

export interface VariableOption {
  value: string
  label?: string
}

export default function VariablePicker({
  variables,
  onPick,
  disabled,
}: {
  variables: VariableOption[]
  onPick: (value: string) => void
  disabled?: boolean
}) {
  if (!variables || variables.length === 0) return null
  return (
    <Popover
      trigger="click"
      placement="bottomLeft"
      content={
        <div style={{ width: 260, maxHeight: 280, overflow: 'auto' }}>
          <div style={{ fontSize: 12, color: '#999', marginBottom: 6 }}>可用变量（点击插入）</div>
          {variables.map((v) => (
            <div
              key={v.value}
              onClick={() => onPick(v.value)}
              style={{
                cursor: 'pointer',
                padding: '5px 8px',
                fontSize: 13,
                borderRadius: 4,
                display: 'flex',
                alignItems: 'center',
                gap: 8,
              }}
              onMouseEnter={(e) => (e.currentTarget.style.background = '#f0f0f0')}
              onMouseLeave={(e) => (e.currentTarget.style.background = 'transparent')}
            >
              <Typography.Text code style={{ fontSize: 12 }}>
                {'{{' + v.value + '}}'}
              </Typography.Text>
              {v.label && (
                <span style={{ color: '#888', fontSize: 12, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {v.label}
                </span>
              )}
            </div>
          ))}
        </div>
      }
    >
      <Button size="small" icon={<FunctionOutlined />} disabled={disabled}>
        插入变量
      </Button>
    </Popover>
  )
}
