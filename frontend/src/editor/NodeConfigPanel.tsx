import { useRef, useState } from 'react'
import { Button, Divider, Empty, Form, Input, InputNumber, Select, Space, Switch, Tag, Typography } from 'antd'
import { DeleteOutlined, PlusOutlined } from '@ant-design/icons'
import type { Node } from '@xyflow/react'
import { NODE_META } from './palette'
import VariablePicker, { type VariableOption } from './VariablePicker'
import type { Datasource, InputField } from '../api/client'

interface NodeInputContext {
  vars: { nodeId: string; saveAs?: string; type?: string }[]
  inputs: InputField[]
  knowledge: string[]
  hasAgentPrompt: boolean
}

interface Props {
  node: Node | null
  onChange: (data: any) => void
  onDelete: () => void
  datasources: Datasource[]
  nodeInputs?: NodeInputContext | null
}

const INPUT_TYPE_OPTIONS = [
  { value: 'text', label: '文本' },
  { value: 'image', label: '图片' },
  { value: 'number', label: '数字' },
  { value: 'select', label: '下拉选择' },
]

export default function NodeConfigPanel({ node, onChange, onDelete, datasources, nodeInputs }: Props) {
  const promptRef = useRef<any>(null)
  const templateRef = useRef<any>(null)
  const paramRefs = useRef<Record<string, any>>({})
  const [activeParam, setActiveParam] = useState<string | null>(null)

  if (!node) return <Empty description="点一个节点进行配置" style={{ marginTop: 80 }} />

  // ---------- 输入节点（start）：配置工作流输入清单 ----------
  if (node.type === 'start') {
    const inputs: InputField[] = (node.data?.inputs as InputField[]) || []
    const setInputs = (next: InputField[]) => onChange({ ...(node.data || {}), inputs: next })
    const updateField = (i: number, patch: Partial<InputField>) =>
      setInputs(inputs.map((f, idx) => (idx === i ? { ...f, ...patch } : f)))
    return (
      <div style={{ padding: 8 }}>
        <Typography.Title level={5} style={{ color: NODE_META.start.color, marginTop: 0 }}>
          输入
        </Typography.Title>
        <Typography.Text type="secondary" style={{ fontSize: 12 }}>
          配置这个工作流需要用户提供哪些输入；测试面板会按此动态渲染表单。
        </Typography.Text>
        {inputs.length === 0 && (
          <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="还没有输入字段" style={{ margin: '12px 0' }} />
        )}
        {inputs.map((f, i) => (
          <div key={i} style={{ border: '1px solid #f0f0f0', borderRadius: 6, padding: 8, marginTop: 8 }}>
            <Space style={{ display: 'flex', marginBottom: 6 }} wrap>
              <Input
                size="small" style={{ width: 110 }} value={f.name} placeholder="变量名（留空自动生成）"
                onChange={(e) => updateField(i, { name: e.target.value })}
              />
              <Input
                size="small" style={{ width: 96 }} value={f.label || ''} placeholder="显示名称"
                onChange={(e) => updateField(i, { label: e.target.value })}
              />
              <Select
                size="small" style={{ width: 78 }} value={f.type || 'text'}
                options={INPUT_TYPE_OPTIONS}
                onChange={(v) => updateField(i, { type: v })}
              />
              <Space size={4}>
                <Switch size="small" checked={!!f.required} onChange={(v) => updateField(i, { required: v })} />
                <Typography.Text style={{ fontSize: 12 }}>必填</Typography.Text>
              </Space>
              <Button
                size="small" type="text" danger icon={<DeleteOutlined />}
                onClick={() => setInputs(inputs.filter((_, idx) => idx !== i))}
              />
            </Space>
            {f.type === 'select' && (
              <Input
                size="small" style={{ marginBottom: 6 }} value={(f.options || []).join(',')}
                placeholder="下拉选项，用逗号分隔"
                onChange={(e) =>
                  updateField(i, { options: e.target.value.split(',').map((s) => s.trim()).filter(Boolean) })
                }
              />
            )}
            <Input
              size="small" value={f.placeholder || ''} placeholder="占位提示（可选）"
              onChange={(e) => updateField(i, { placeholder: e.target.value })}
            />
          </div>
        ))}
        <Button
          type="dashed" block style={{ marginTop: 8 }} icon={<PlusOutlined />}
          onClick={() => setInputs([...inputs, { name: '', label: '', type: 'text', required: false }])}
        >
          添加输入
        </Button>
      </div>
    )
  }

  // ---------- 步骤节点：llm / decision / http / end / template ----------
  const cfg: any = node.data?.config || { type: node.type }
  const meta = NODE_META[node.type as string] || NODE_META.llm
  const set = (patch: any) => onChange({ ...(node.data || {}), config: { ...cfg, ...patch } })

  // 可用变量（按拓扑动态计算）：前序节点产物 + 工作流输入 + 静态提示词
  const varOptions: VariableOption[] = []
  if (nodeInputs) {
    for (const v of nodeInputs.vars) varOptions.push({ value: v.saveAs as string, label: `来自「${v.nodeId}」` })
    for (const f of nodeInputs.inputs) varOptions.push({ value: f.name, label: `输入「${f.label || f.name}」` })
    if (nodeInputs.hasAgentPrompt) varOptions.push({ value: 'system_prompt', label: '静态提示词' })
  }
  const insertAt = (el: any, current: string, value: string, apply: (next: string) => void) => {
    // antd 的 Input / TextArea ref 是包装对象，取原生元素
    const native = el?.resizableTextArea?.textArea ?? el?.input ?? el ?? null
    const start = native?.selectionStart ?? current.length
    const end = native?.selectionEnd ?? current.length
    const token = `{{${value}}}`
    const next = current.slice(0, start) + token + current.slice(end)
    apply(next)
    requestAnimationFrame(() => {
      if (native) {
        native.focus()
        const pos = start + token.length
        native.setSelectionRange(pos, pos)
      }
    })
  }

  const showInputPreview = nodeInputs && node.type !== 'start'
  const noInput = nodeInputs && nodeInputs.vars.length === 0 && nodeInputs.inputs.length === 0 && nodeInputs.knowledge.length === 0 && !nodeInputs.hasAgentPrompt

  return (
    <div style={{ padding: 8 }}>
      {showInputPreview && (
        <div style={{ background: '#fafafa', borderRadius: 6, padding: '6px 8px', marginBottom: 10, fontSize: 12 }}>
          <Typography.Text strong style={{ fontSize: 12 }}>
            本节点可用的输入
          </Typography.Text>
          {noInput ? (
            <div style={{ color: '#999', marginTop: 2 }}>（暂无上游输入）</div>
          ) : (
            <>
              {nodeInputs!.vars.map((v) => (
                <div key={v.nodeId} style={{ color: '#555' }}>
                  • 前序「{v.nodeId}」→ <Typography.Text code>{v.saveAs}</Typography.Text>
                </div>
              ))}
              {nodeInputs!.inputs.map((f) => (
                <div key={f.name} style={{ color: '#555' }}>
                  • 工作流输入「{f.label || f.name}」
                </div>
              ))}
              {nodeInputs!.knowledge.map((k) => (
                <div key={k} style={{ color: '#555' }}>
                  • 知识「{k}」
                </div>
              ))}
              {nodeInputs!.hasAgentPrompt && <div style={{ color: '#555' }}>• 静态提示词（Agent）</div>}
            </>
          )}
        </div>
      )}
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
            <Input.TextArea
              ref={promptRef}
              rows={5}
              value={cfg.prompt || ''}
              placeholder="这个环节让 Agent 做什么。前序节点产物会自动注入模型上下文，无需手动引用变量。"
              onChange={(e) => set({ prompt: e.target.value })}
            />
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

      {node.type === 'template' && (
        <>
          <Form.Item
            label={
              <Space size={4}>
                模板内容
                <VariablePicker variables={varOptions} onPick={(v) => insertAt(templateRef.current, cfg.template || '', v, (n) => set({ template: n }))} />
              </Space>
            }
            style={{ marginBottom: 12 }}
          >
            <Input.TextArea
              ref={templateRef}
              rows={8}
              value={cfg.template || ''}
              placeholder={'通用文本模板：支持 {{system_prompt}}（静态系统提示）和 {{order}} 等前序结果变量'}
              onChange={(e) => set({ template: e.target.value })}
            />
          </Form.Item>
          <Typography.Text type="secondary" style={{ fontSize: 12 }}>
            纯函数拼接，不经过模型；结果存到「保存为」的变量。
          </Typography.Text>
        </>
      )}

      {node.type === 'http' && (() => {
        const ds = datasources.find((d) => d.name === cfg.datasource)
        const paramDefs = ds?.param_defs || []
        const params = cfg.params || {}
        const setParam = (name: string, value: unknown) => set({ params: { ...params, [name]: value } })
        const renderInput = (p: { name: string; type?: string; placeholder?: string; options?: string[] }) => {
          const focus = () => setActiveParam(p.name)
          if (p.type === 'select') {
            return (
              <Select
                style={{ width: '100%' }}
                value={(params[p.name] as string) || undefined}
                placeholder={p.placeholder || '请选择'}
                options={(p.options || []).map((o) => ({ value: o, label: o }))}
                onChange={(v) => setParam(p.name, v)}
                onFocus={focus}
              />
            )
          }
          if (p.type === 'number') {
            return (
              <InputNumber
                style={{ width: '100%' }}
                value={params[p.name] as number | undefined}
                placeholder={p.placeholder || '请输入数字'}
                onChange={(v) => setParam(p.name, v)}
                onFocus={focus}
              />
            )
          }
          return (
            <Input
              ref={(el) => {
                paramRefs.current[p.name] = el
              }}
              value={(params[p.name] as string) || ''}
              placeholder={p.placeholder || '请输入'}
              onChange={(e) => setParam(p.name, e.target.value)}
              onFocus={focus}
            />
          )
        }
        return (
          <>
            <Form.Item label="数据源" style={{ marginBottom: 12 }}>
              <Select
                value={cfg.datasource || undefined}
                placeholder="选择数据源"
                options={datasources.map((d) => ({ value: d.name, label: d.name }))}
                onChange={(v) => set({ datasource: v })}
              />
            </Form.Item>
            <Form.Item
              label={
                <Space size={4}>
                  参数
                  <VariablePicker
                    variables={varOptions}
                    onPick={(v) => {
                      const t = activeParam ?? paramDefs[0]?.name
                      if (t) insertAt(paramRefs.current[t], String(params[t] ?? ''), v, (n) => setParam(t, n))
                    }}
                  />
                </Space>
              }
              style={{ marginBottom: 12 }}
            >
              {paramDefs.length === 0 ? (
                <Typography.Text type="secondary" style={{ fontSize: 12 }}>
                  该数据源未声明参数。
                </Typography.Text>
              ) : (
                paramDefs.map((p: any) => (
                  <div key={p.name} style={{ marginBottom: 10 }}>
                    <div style={{ marginBottom: 4 }}>
                      <Typography.Text strong style={{ fontSize: 13 }}>
                        {p.label || p.name}
                      </Typography.Text>
                      {p.required && <Tag color="red" style={{ marginLeft: 6 }}>必填</Tag>}
                    </div>
                    {renderInput(p)}
                    <div style={{ color: '#999', fontSize: 11, marginTop: 2 }}>参数名 {p.name} · 可用 {'{{变量}}'} 引用前面结果</div>
                  </div>
                ))
              )}
            </Form.Item>
          </>
        )
      })()}

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
