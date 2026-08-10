import { Button, Popconfirm, Space, Table, Tag, message } from 'antd'
import { api } from '../../api/client'
import type { Agent, Version } from '../../api/client'

export default function PublishTab({
  agentId,
  agent,
  versions,
  onChanged,
}: {
  agentId: string
  agent: Agent
  versions: Version[]
  onChanged: () => void
}) {
  const publish = async (v: Version) => {
    try {
      await api.publish(v.id, { approved_by: 'admin' })
      message.success('已发布')
      onChanged()
    } catch (e: any) {
      message.error(e.response?.data?.message || '发布失败')
    }
  }
  const rollback = async (v: Version) => {
    try {
      await api.rollback(agentId, { target_version_id: v.id, approved_by: 'admin' })
      message.success('已回滚')
      onChanged()
    } catch (e: any) {
      message.error(e.response?.data?.message || '回滚失败')
    }
  }

  return (
    <div style={{ maxWidth: 900 }}>
      <Table
        rowKey="id"
        dataSource={[...versions].reverse()}
        pagination={false}
        columns={[
          { title: '版本', render: (_, v) => `V${v.version_no}` },
          {
            title: '状态',
            dataIndex: 'status',
            render: (s) =>
              s === 'published' ? (
                <Tag color="green">已发布</Tag>
              ) : s === 'draft' ? (
                <Tag color="blue">草稿</Tag>
              ) : (
                <Tag>已回滚</Tag>
              ),
          },
          { title: '提示词', dataIndex: 'prompt', ellipsis: true },
          {
            title: '当前',
            render: (_, v) => (agent.current_version_id === v.id ? <Tag color="green">线上</Tag> : null),
          },
          {
            title: '操作',
            render: (_, v) => (
              <Space>
                {v.status === 'draft' && (
                  <Button size="small" type="primary" onClick={() => publish(v)}>
                    发布
                  </Button>
                )}
                {v.status !== 'draft' && agent.current_version_id !== v.id && (
                  <Popconfirm title="回滚到此版本？" onConfirm={() => rollback(v)}>
                    <Button size="small">回滚</Button>
                  </Popconfirm>
                )}
              </Space>
            ),
          },
        ]}
      />
    </div>
  )
}
