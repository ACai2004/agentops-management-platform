import { Button, Divider, Empty, Form, Input, Select, Space, Switch, Typography } from 'antd'
import type { Node } from '@xyflow/react'
import { NODE_META } from './palette'
import type { Datasource } from '../api/client'

interface Props {
  node: Node | null
  onChange: (cfg: any) => void
  onDelete: () => void
  datasources: Datasource[]
}

export default function NodeConfigPanel({ node, onChange, onDelete, datasources }: Props) {
  if (!node) return <Empty description="点一个节点进行配置" style={{ marginTop: 80 }} />
  const cfg: any = node.data?.config || { type: node.type }
  const meta = NODE_META[node.type as string] || NODE_META.llm
  const set = (patch: any) => onChange({ ...cfg, ...patch })

  return (
    <div style={{ padding: 8 }}>
      <Typography.Title level={5} style={{ color: meta.color, marginTop: 0 }}>
        {meta.label}
      </Typography.Title>

      {node.type !== 'end' && (
        <>
          <Form.Item label="保存为（结果变量名）" style={{ marginBottom: 12 }}>
            <Input value={cfg.save_as || ''} placeholder="如：output" onChange={(e) => set({ save_as: e.target.value })} />
          </Form.Item>
        </>
      )}

      {node.type === 'llm' && (
        <>
          <Form.Item label="提示词" style={{ marginBottom: 12 }}>
            <Input.TextArea rows={5} value={cfg.prompt || ''} placeholder="这个环节让 Agent 做什么" onChange={(e) => set({ prompt: e.target.value })} />
          </Form.Item>
          <Form.Item label="识别图片（小票）" style={{ marginBottom: 12 }}>
            <Switch checked={!!cfg.image_input} onChange={(v) => set({ image_input: v })} />
          </Form.Item>
        </>
      )}

      {node.type === 'decision' && (
        <>
          <Form.Item label="判断指令" style={{ marginBottom: 12 }}>
            <Input.TextArea rows={4} value={cfg.prompt || ''} placeholder="让 Agent 判断什么" onChange={(e) => set({ prompt: e.target.value })} />
          </Form.Item>
          <Typography.Text type="secondary" style={{ fontSize: 12 }}>
            分支：在画布上从本节点连出多条线，双击连线可改分支值。
          </Typography.Text>
        </>
      )}

      {node.type === 'http' && (
        <>
          <Form.Item label="数据源" style={{ marginBottom: 12 }}>
            <Select
              value={cfg.datasource || undefined}
              placeholder="选择数据源"
              options={datasources.map((d) => ({ value: d.name, label: d.name }))}
              onChange={(v) => set({ datasource: v })}
            />
          </Form.Item>
          <Form.Item label="参数（可用 {{变量}} 引用前面结果）" style={{ marginBottom: 12 }}>
            {Object.entries(cfg.params || {}).map(([k, v]) => (
              <Space key={k} style={{ display: 'flex', marginBottom: 8 }}>
                <Input size="small" style={{ width: 120 }} value={k} onChange={(e) => { const p = { ...(cfg.params || {}) }; delete p[k]; p[e.target.value] = v as string; set({ params: p }) }} />
                <Input size="small" style={{ width: 180 }} value={v as string} onChange={(e) => set({ params: { ...(cfg.params || {}), [k]: e.target.value } })} />
              </Space>
            ))}
            <Button size="small" onClick={() => set({ params: { ...(cfg.params || {}), 参数: '' } })}>+ 参数</Button>
          </Form.Item>
        </>
      )}

      {node.type === 'llm' && (
        <Form.Item label="模型设置（可选）" style={{ marginBottom: 12 }}>
          <Input
            placeholder="如 openrouter/qwen/qwen2.5-vl-72b-instruct"
            value={cfg.model_settings?.model || ''}
            onChange={(e) => set({ model_settings: { ...(cfg.model_settings || {}), model: e.target.value } })}
          />
        </Form.Item>
      )}

      <Divider />
      <Button danger size="small" onClick={onDelete}>
        删除节点
      </Button>
    </div>
  )
}
