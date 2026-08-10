import { useEffect, useState } from 'react'
import { Button, Form, Input, Modal, Space, Table, Typography, message } from 'antd'
import { PlusOutlined } from '@ant-design/icons'
import { api } from '../api/client'
import type { Capability } from '../api/client'

export default function CapabilityList() {
  const [items, setItems] = useState<Capability[]>([])
  const [open, setOpen] = useState(false)
  const [form] = Form.useForm()

  const load = () => api.listCapabilities().then(setItems).catch(() => message.error('加载失败'))
  useEffect(() => {
    load()
  }, [])

  const submit = async () => {
    const v = await form.validateFields()
    try {
      await api.createCapability(v)
      message.success('已创建')
      setOpen(false)
      form.resetFields()
      load()
    } catch (e: any) {
      message.error(e.response?.data?.message || '创建失败')
    }
  }

  return (
    <div style={{ maxWidth: 1100 }}>
      <Space style={{ marginBottom: 16 }} align="center">
        <Typography.Title level={4} style={{ margin: 0 }}>
          能力
        </Typography.Title>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => setOpen(true)}>
          新建能力
        </Button>
      </Space>
      <Table
        rowKey="name"
        dataSource={items}
        pagination={false}
        columns={[
          { title: '名称', dataIndex: 'name' },
          { title: '描述', dataIndex: 'description', ellipsis: true },
          { title: '行为指令', dataIndex: 'behavior_instruction', ellipsis: true },
        ]}
      />
      <Modal title="新建能力" open={open} onOk={submit} onCancel={() => setOpen(false)} width={560}>
        <Form form={form} layout="vertical">
          <Form.Item name="name" label="名称" rules={[{ required: true }]}>
            <Input placeholder="如：满意度判断" />
          </Form.Item>
          <Form.Item name="description" label="描述">
            <Input placeholder="这个能力是做什么的" />
          </Form.Item>
          <Form.Item name="behavior_instruction" label="行为指令" rules={[{ required: true }]}>
            <Input.TextArea rows={4} placeholder="作为节点的提示词片段" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}
