import { useState } from 'react'
import { Button, Card, Input, InputNumber, Select, Space, Tag, Timeline, Typography, Upload, message } from 'antd'
import { UploadOutlined } from '@ant-design/icons'
import { api } from '../../api/client'
import type { InputField, Trace, Version } from '../../api/client'

export default function TestTab({ agentId, version }: { agentId: string; version: Version | null }) {
  const [input, setInput] = useState('') // 兼容：无输入清单时的旧文本输入
  const [values, setValues] = useState<Record<string, unknown>>({})
  const [images, setImages] = useState<Record<string, string>>({})
  const [running, setRunning] = useState(false)
  const [trace, setTrace] = useState<Trace | null>(null)

  const fields: InputField[] = (version?.workflow_config?.inputs as InputField[] | undefined) || []

  const run = async () => {
    if (!version) return message.warning('请先创建版本')
    setRunning(true)
    try {
      if (fields.length === 0) {
        // 旧工作流：无输入清单，走平铺文本
        const t = await api.run(agentId, { input, version_id: version.id, env: 'test' })
        setTrace(t)
      } else {
        const inputs: Record<string, unknown> = { ...values }
        for (const f of fields) if (f.type === 'image' && images[f.name]) inputs[f.name] = images[f.name]
        const t = await api.run(agentId, { inputs, version_id: version.id, env: 'test' })
        setTrace(t)
      }
    } catch (e: any) {
      message.error(e.response?.data?.message || '运行失败')
    } finally {
      setRunning(false)
    }
  }

  const onFile = (name: string, file: File) => {
    const reader = new FileReader()
    reader.onload = () => setImages((m) => ({ ...m, [name]: reader.result as string }))
    reader.readAsDataURL(file)
    return false
  }

  const renderOutput = (v: unknown) => (typeof v === 'string' ? v : JSON.stringify(v, null, 2))

  const renderField = (f: InputField) => {
    if (f.type === 'image') {
      const dataUrl = images[f.name]
      return (
        <div>
          <Space>
            <Upload beforeUpload={(file) => onFile(f.name, file)} showUploadList={false} accept="image/*">
              <Button icon={<UploadOutlined />}>{dataUrl ? '重新选择图片' : `上传${f.label || f.name}`}</Button>
            </Upload>
            {dataUrl && (
              <Button size="small" onClick={() => setImages((m) => ({ ...m, [f.name]: '' }))}>
                移除
              </Button>
            )}
          </Space>
          {dataUrl && (
            <div style={{ marginTop: 8 }}>
              <img
                src={dataUrl}
                alt={f.label || f.name}
                style={{ maxWidth: 220, maxHeight: 220, borderRadius: 8, border: '1px solid #f0f0f0' }}
              />
            </div>
          )}
        </div>
      )
    }
    if (f.type === 'number') {
      return (
        <InputNumber
          style={{ width: '100%' }}
          value={values[f.name] as number | undefined}
          placeholder={f.placeholder || '请输入数字'}
          onChange={(v) => setValues((m) => ({ ...m, [f.name]: v }))}
        />
      )
    }
    if (f.type === 'select') {
      return (
        <Select
          style={{ width: '100%' }}
          value={values[f.name] as string | undefined}
          placeholder={f.placeholder || '请选择'}
          options={(f.options || []).map((o) => ({ value: o, label: o }))}
          onChange={(v) => setValues((m) => ({ ...m, [f.name]: v }))}
        />
      )
    }
    // text
    return (
      <Input.TextArea
        rows={2}
        value={values[f.name] as string | undefined}
        placeholder={f.placeholder || '补充说明（可选）'}
        onChange={(e) => setValues((m) => ({ ...m, [f.name]: e.target.value }))}
      />
    )
  }

  return (
    <div style={{ maxWidth: 760 }}>
      <Card>
        {fields.length === 0 ? (
          <Input.TextArea
            rows={3}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="输入内容…（该工作流未声明输入清单）"
          />
        ) : (
          fields.map((f) => (
            <div key={f.name} style={{ marginBottom: 12 }}>
              <div style={{ marginBottom: 6 }}>
                <Typography.Text strong>{f.label || f.name}</Typography.Text>
                {f.required && <Tag color="red" style={{ marginLeft: 6 }}>必填</Tag>}
              </div>
              {renderField(f)}
            </div>
          ))
        )}
        <Button type="primary" loading={running} onClick={run} style={{ marginTop: 4 }}>
          运行
        </Button>
      </Card>

      {trace && (
        <Card title="运行结果" style={{ marginTop: 16 }}>
          <Typography.Paragraph>
            <b>回复：</b>
            {trace.output}
          </Typography.Paragraph>
          <Typography.Title level={5}>Trace 步骤</Typography.Title>
          <Timeline
            items={trace.steps.map((s, i) => ({
              key: i,
              color: s.node_type === 'http' ? 'green' : s.node_type === 'decision' ? 'orange' : 'blue',
              content: (
                <div>
                  <b>{s.node_id}</b> <Tag>{s.node_type}</Tag>
                  {s.branch && <Tag color="purple">→ {s.branch}</Tag>}
                  <div style={{ color: '#666', fontSize: 12, whiteSpace: 'pre-wrap' }}>
                    {renderOutput(s.output)}
                  </div>
                </div>
              ),
            }))}
          />
        </Card>
      )}
    </div>
  )
}
