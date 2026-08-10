import { useEffect, useState } from 'react'
import { Button, Card, Descriptions, Input, List, Space, Steps, Tag, Typography, message } from 'antd'
import { api } from '../../api/client'
import type { Plan, Trace } from '../../api/client'

export default function OptimizeTab({
  agentId,
  onChanged,
}: {
  agentId: string
  onChanged: () => void
}) {
  const [traces, setTraces] = useState<Trace[]>([])
  const [selected, setSelected] = useState<Trace | null>(null)
  const [text, setText] = useState('')
  const [plan, setPlan] = useState<Plan | null>(null)
  const [busy, setBusy] = useState(false)

  const load = () => api.listTraces({ agent_id: agentId, limit: 20 }).then(setTraces).catch(() => {})
  useEffect(() => {
    load()
  }, [agentId])

  const optimize = async () => {
    if (!selected) return message.warning('先选一条运行记录')
    if (!text.trim()) return message.warning('请输入反馈')
    setBusy(true)
    try {
      const fb = await api.addFeedback(selected.id, { text })
      const p = await api.optimize(fb.id)
      setPlan(p)
    } catch (e: any) {
      message.error(e.response?.data?.message || '优化失败')
    } finally {
      setBusy(false)
    }
  }

  const apply = async () => {
    if (!plan) return
    try {
      await api.applyPlan(plan.id, { approved_by: 'admin' })
      message.success('已应用，生成新版本')
      setPlan(null)
      onChanged()
    } catch (e: any) {
      message.error(e.response?.data?.message || '应用失败')
    }
  }

  const reject = async () => {
    if (!plan) return
    await api.rejectPlan(plan.id)
    setPlan(null)
    message.info('已拒绝')
  }

  return (
    <div style={{ maxWidth: 860 }}>
      <Steps
        size="small"
        current={plan ? 2 : 0}
        style={{ marginBottom: 16 }}
        items={[{ title: '选记录' }, { title: '反馈' }, { title: '方案' }]}
      />
      <Space align="start" style={{ width: '100%' }}>
        <List
          style={{ width: 320, maxHeight: 400, overflow: 'auto' }}
          dataSource={traces}
          locale={{ emptyText: '暂无运行记录' }}
          renderItem={(t) => (
            <List.Item
              onClick={() => setSelected(t)}
              style={{
                cursor: 'pointer',
                background: selected?.id === t.id ? '#e6f4ff' : undefined,
                padding: '4px 12px',
              }}
            >
              <div style={{ fontSize: 13 }}>{t.input}</div>
            </List.Item>
          )}
        />
        <div style={{ flex: 1 }}>
          <Card>
            <Typography.Text type="secondary">对选中的运行记录打反馈：</Typography.Text>
            <Input.TextArea
              rows={3}
              value={text}
              onChange={(e) => setText(e.target.value)}
              placeholder="如：回复太机械，没有追问原因"
              style={{ marginTop: 8 }}
            />
            <Button type="primary" loading={busy} onClick={optimize} style={{ marginTop: 8 }}>
              优化
            </Button>
          </Card>
          {plan && (
            <Card title="优化方案" style={{ marginTop: 16 }}>
              <Descriptions column={1} size="small">
                <Descriptions.Item label="问题分析">{plan.problem_analysis}</Descriptions.Item>
                <Descriptions.Item label="根因">{plan.root_cause}</Descriptions.Item>
                <Descriptions.Item label="建议">{plan.suggestions.join('；')}</Descriptions.Item>
              </Descriptions>
              <Typography.Title level={5} style={{ marginTop: 12 }}>
                修改内容
              </Typography.Title>
              {plan.changes.map((c, i) => (
                <div key={i} style={{ padding: '6px 0', borderBottom: '1px solid #f0f0f0' }}>
                  <Tag color="blue">{c.operation}</Tag> <span>{c.description}</span>
                </div>
              ))}
              <Space style={{ marginTop: 16 }}>
                <Button type="primary" onClick={apply}>
                  应用生成新版本
                </Button>
                <Button onClick={reject}>拒绝</Button>
              </Space>
            </Card>
          )}
        </div>
      </Space>
    </div>
  )
}
