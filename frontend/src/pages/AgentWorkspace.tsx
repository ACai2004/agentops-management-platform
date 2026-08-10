import { useEffect, useState } from 'react'
import { Button, Result, Space, Spin, Tabs, Typography, message } from 'antd'
import { useNavigate, useParams } from 'react-router-dom'
import { api } from '../api/client'
import type { Agent, Version } from '../api/client'
import BindingsTab from './workspace/BindingsTab'
import OptimizeTab from './workspace/OptimizeTab'
import PublishTab from './workspace/PublishTab'
import TestTab from './workspace/TestTab'
import TracesTab from './workspace/TracesTab'
import WorkflowTab from './workspace/WorkflowTab'

export default function AgentWorkspace() {
  const { id = '' } = useParams()
  const [agent, setAgent] = useState<Agent | null>(null)
  const [versions, setVersions] = useState<Version[]>([])
  const [loading, setLoading] = useState(true)
  const navigate = useNavigate()

  const load = async () => {
    try {
      const a = await api.getAgent(id)
      const vs = await api.listVersions(id)
      setAgent(a)
      setVersions(vs)
    } catch {
      message.error('加载失败')
    } finally {
      setLoading(false)
    }
  }
  useEffect(() => {
    setLoading(true)
    load()
  }, [id])

  if (loading) return <Spin style={{ display: 'block', margin: '80px auto' }} />
  if (!agent)
    return (
      <Result
        status="404"
        title="Agent 不存在"
        extra={
          <Button onClick={() => navigate('/')}>返回</Button>
        }
      />
    )

  // 当前编辑的版本：最新草稿，否则线上（发布版本）
  const draft = versions.find((v) => v.status === 'draft')
  const current = versions.find((v) => v.id === agent.current_version_id)
  const editing = draft || current || null

  return (
    <div style={{ maxWidth: 1200 }}>
      <Space style={{ marginBottom: 12 }} align="center">
        <Typography.Title level={4} style={{ margin: 0 }}>
          {agent.name}
        </Typography.Title>
        <Typography.Text type="secondary">
          线上 V{current?.version_no ?? '-'}
          {draft ? ` · 草稿 V${draft.version_no} 编辑中` : ''}
        </Typography.Text>
      </Space>
      <Tabs
        defaultActiveKey="workflow"
        items={[
          {
            key: 'workflow',
            label: '工作流',
            children: <WorkflowTab agentId={id} version={editing} onChanged={load} />,
          },
          {
            key: 'test',
            label: '测试',
            children: <TestTab agentId={id} version={editing} />,
          },
          { key: 'traces', label: '运行记录', children: <TracesTab agentId={id} /> },
          { key: 'optimize', label: '优化', children: <OptimizeTab agentId={id} onChanged={load} /> },
          {
            key: 'publish',
            label: '版本发布',
            children: <PublishTab agentId={id} agent={agent} versions={versions} onChanged={load} />,
          },
          {
            key: 'bindings',
            label: '能力与知识',
            children: <BindingsTab version={editing} onChanged={load} />,
          },
        ]}
      />
    </div>
  )
}
