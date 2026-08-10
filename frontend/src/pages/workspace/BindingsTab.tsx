import { useEffect, useState } from 'react'
import { Card, Select, Space, Tag, Typography, message } from 'antd'
import { api } from '../../api/client'
import type { Capability, Knowledge, Version } from '../../api/client'

export default function BindingsTab({
  version,
  onChanged,
}: {
  version: Version | null
  onChanged: () => void
}) {
  const [knowledge, setKnowledge] = useState<Knowledge[]>([])
  const [capabilities, setCapabilities] = useState<Capability[]>([])

  useEffect(() => {
    api.listKnowledge().then(setKnowledge).catch(() => {})
    api.listCapabilities().then(setCapabilities).catch(() => {})
  }, [])

  if (!version) return <Typography.Text type="secondary">暂无版本</Typography.Text>

  const bindK = async (name: string) => {
    try {
      await api.bindKnowledge(version.id, { name })
      message.success('已绑定知识')
      onChanged()
    } catch (e: any) {
      message.error(e.response?.data?.message || '绑定失败')
    }
  }
  const unbindK = async (name: string) => {
    try {
      await api.unbindKnowledge(version.id, name)
      onChanged()
    } catch (e: any) {
      message.error(e.response?.data?.message || '解绑失败')
    }
  }
  const bindC = async (name: string) => {
    try {
      await api.bindCapability(version.id, { name })
      onChanged()
    } catch (e: any) {
      message.error(e.response?.data?.message || '绑定失败')
    }
  }

  const boundKnowledge = version.knowledge_bindings || []
  const boundCapabilities = Object.keys(version.capability_bindings || {})

  return (
    <Space direction="vertical" style={{ width: '100%', maxWidth: 720 }}>
      <Card title="知识绑定">
        <Typography.Paragraph type="secondary" style={{ fontSize: 13 }}>
          绑定的知识会注入到 Agent 的上下文，回答时自动基于这些资料；改知识即生效。
        </Typography.Paragraph>
        <Select
          placeholder="选择要绑定的知识"
          style={{ width: 300 }}
          onSelect={(v) => bindK(v as string)}
          options={knowledge.filter((k) => !boundKnowledge.includes(k.name)).map((k) => ({ value: k.name, label: k.name }))}
        />
        <div style={{ marginTop: 12 }}>
          {boundKnowledge.map((name) => (
            <Tag key={name} closable onClose={() => unbindK(name)} style={{ marginBottom: 4 }}>
              {name}
            </Tag>
          ))}
        </div>
      </Card>
      <Card title="能力绑定">
        <Select
          placeholder="选择要绑定的能力"
          style={{ width: 300 }}
          onSelect={(v) => bindC(v as string)}
          options={capabilities.filter((c) => !boundCapabilities.includes(c.name)).map((c) => ({ value: c.name, label: c.name }))}
        />
        <div style={{ marginTop: 12 }}>
          {boundCapabilities.map((name) => (
            <Tag key={name} color="blue" style={{ marginBottom: 4 }}>
              {name}
            </Tag>
          ))}
        </div>
      </Card>
    </Space>
  )
}
