import { useEffect, useState } from 'react'
import { Button, Card, Empty, Input, Space, Typography, message } from 'antd'
import { api } from '../../api/client'
import type { Datasource, Version } from '../../api/client'
import WorkflowCanvas from '../../editor/WorkflowCanvas'

export default function WorkflowTab({
  agentId,
  version,
  onChanged,
}: {
  agentId: string
  version: Version | null
  onChanged: () => void
}) {
  const [datasources, setDatasources] = useState<Datasource[]>([])
  const [promptText, setPromptText] = useState('')
  const [savingPrompt, setSavingPrompt] = useState(false)
  useEffect(() => {
    api.listDatasources().then(setDatasources).catch(() => {})
  }, [])
  useEffect(() => {
    setPromptText(version?.prompt ?? '')
  }, [version?.id])

  const savePrompt = async () => {
    if (!version) return
    setSavingPrompt(true)
    try {
      await api.updateDraft(version.id, { prompt: promptText })
      message.success('系统提示词已保存')
      onChanged()
    } catch (e: any) {
      message.error(e.response?.data?.message || '保存失败')
    } finally {
      setSavingPrompt(false)
    }
  }

  const startDraft = async () => {
    try {
      await api.createDraft(agentId)
      message.success('已创建草稿')
      onChanged()
    } catch (e: any) {
      message.error(e.response?.data?.message || '创建草稿失败')
    }
  }

  if (!version) return <Empty description="还没有版本，请先新建草稿" />

  const readOnly = version.status !== 'draft'

  return (
    <div>
      <Space style={{ marginBottom: 12 }}>
        <span>
          编辑版本：V{version.version_no}（{version.status === 'draft' ? '草稿' : '线上'}）
        </span>
        {readOnly && (
          <Button type="primary" size="small" onClick={startDraft}>
            新建草稿再编辑
          </Button>
        )}
      </Space>
      <Card size="small" style={{ marginBottom: 12 }}>
        <Space style={{ width: '100%', justifyContent: 'space-between', marginBottom: 8 }}>
          <Typography.Text strong>系统提示词（Agent 角色与规则）</Typography.Text>
          <Button size="small" type="primary" loading={savingPrompt} disabled={readOnly} onClick={savePrompt}>
            保存提示词
          </Button>
        </Space>
        <Input.TextArea
          rows={4}
          value={promptText}
          disabled={readOnly}
          onChange={(e) => setPromptText(e.target.value)}
          placeholder="Agent 的系统提示词：角色、规则、语气…（只读时禁用，新建草稿后可编辑）"
        />
      </Card>
      <WorkflowCanvas
        key={version.id}
        version={version}
        readOnly={readOnly}
        onSaved={onChanged}
        datasources={datasources}
        agentId={agentId}
      />
    </div>
  )
}
