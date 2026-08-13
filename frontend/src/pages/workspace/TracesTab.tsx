import { useEffect, useState } from 'react'
import { Empty, List, Modal, Tag, Timeline, Typography, message } from 'antd'
import { api } from '../../api/client'
import type { Trace } from '../../api/client'

export default function TracesTab({ agentId }: { agentId: string }) {
  const [traces, setTraces] = useState<Trace[]>([])
  const [detail, setDetail] = useState<Trace | null>(null)

  const load = () =>
    api.listTraces({ agent_id: agentId, limit: 50 }).then(setTraces).catch(() => message.error('加载失败'))
  useEffect(() => {
    load()
  }, [agentId])

  return (
    <div style={{ maxWidth: 760 }}>
      <List
        dataSource={traces}
        locale={{ emptyText: <Empty description="还没有运行记录，去「测试」页跑一次" /> }}
        renderItem={(t) => (
          <List.Item onClick={() => setDetail(t)} style={{ cursor: 'pointer' }}>
            <List.Item.Meta
              title={<span style={{ fontSize: 14 }}>{t.input}</span>}
              description={`${t.created_at ? new Date(t.created_at).toLocaleString() : ''} · ${t.version_id.slice(0, 8)}`}
            />
            <Tag color={t.env === 'live' ? 'green' : 'blue'}>{t.env}</Tag>
          </List.Item>
        )}
      />
      <Modal title="Trace 详情" open={!!detail} onCancel={() => setDetail(null)} footer={null} width={760}>
        {detail && (
          <>
            <Typography.Paragraph>
              <b>输入：</b>
              {detail.input}
            </Typography.Paragraph>
            {detail.inputs && Object.keys(detail.inputs).length > 0 && (
              <Typography.Paragraph>
                <b>输入项：</b>
                {Object.entries(detail.inputs).map(([k, v]) => (
                  <span key={k} style={{ marginRight: 12, whiteSpace: 'pre-wrap' }}>
                    {k}: {typeof v === 'string' && v.length > 80 ? `${v.slice(0, 80)}…` : String(v)}
                  </span>
                ))}
              </Typography.Paragraph>
            )}
            <Typography.Paragraph>
              <b>输出：</b>
              {detail.output}
            </Typography.Paragraph>
            <Timeline
              items={detail.steps.map((s, i) => ({
                key: i,
                color: s.node_type === 'http' ? 'green' : s.node_type === 'decision' ? 'orange' : 'blue',
                content: (
                  <div>
                    <b>{s.node_id}</b> <Tag>{s.node_type}</Tag>
                    {s.branch && <Tag color="purple">→ {s.branch}</Tag>}
                    <div style={{ color: '#666', fontSize: 12, whiteSpace: 'pre-wrap' }}>
                      {typeof s.output === 'string' ? s.output : JSON.stringify(s.output, null, 2)}
                    </div>
                  </div>
                ),
              }))}
            />
          </>
        )}
      </Modal>
    </div>
  )
}
