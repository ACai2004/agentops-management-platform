import { useEffect, useState } from 'react'
import { Button, Card, Col, Empty, Row, Space, Typography, message } from 'antd'
import { PlusOutlined } from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import { api } from '../api/client'
import type { Agent } from '../api/client'

export default function AgentList() {
  const [agents, setAgents] = useState<Agent[]>([])
  const [loading, setLoading] = useState(true)
  const navigate = useNavigate()

  const load = () => {
    api
      .listAgents()
      .then(setAgents)
      .catch((e) => message.error(e.response?.data?.message || '加载失败'))
      .finally(() => setLoading(false))
  }
  useEffect(() => {
    load()
  }, [])

  const create = async () => {
    try {
      const a = await api.createAgent({ name: '新建 Agent' })
      message.success('已创建')
      navigate(`/agents/${a.id}`)
    } catch (e: any) {
      message.error(e.response?.data?.message || '创建失败')
    }
  }

  return (
    <div style={{ maxWidth: 1200 }}>
      <Space style={{ marginBottom: 16 }} align="center">
        <Typography.Title level={4} style={{ margin: 0 }}>
          Agent 列表
        </Typography.Title>
        <Button type="primary" icon={<PlusOutlined />} onClick={create}>
          新建 Agent
        </Button>
      </Space>
      {!loading && agents.length === 0 ? (
        <Empty description="还没有 Agent，点「新建 Agent」开始" />
      ) : (
        <Row gutter={[16, 16]}>
          {agents.map((a) => (
            <Col key={a.id} xs={24} sm={12} md={8} lg={6}>
              <Card hoverable onClick={() => navigate(`/agents/${a.id}`)}>
                <Card.Meta title={a.name} description={a.description || '暂无描述'} />
              </Card>
            </Col>
          ))}
        </Row>
      )}
    </div>
  )
}
