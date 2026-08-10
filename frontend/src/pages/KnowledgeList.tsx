import { useEffect, useState } from 'react'
import { Button, Form, Input, Modal, Space, Table, Tag, Typography, message } from 'antd'
import { PlusOutlined } from '@ant-design/icons'
import { api } from '../api/client'
import type { Knowledge } from '../api/client'

export default function KnowledgeList() {
  const [items, setItems] = useState<Knowledge[]>([])
  const [open, setOpen] = useState(false)
  const [editing, setEditing] = useState<Knowledge | null>(null)
  const [form] = Form.useForm()

  const load = () => api.listKnowledge().then(setItems).catch(() => message.error('加载失败'))
  useEffect(() => {
    load()
  }, [])

  const openCreate = () => {
    setEditing(null)
    form.resetFields()
    setOpen(true)
  }
  const openEdit = (k: Knowledge) => {
    setEditing(k)
    form.setFieldsValue({ name: k.name, kind: k.kind, content: k.content })
    setOpen(true)
  }

  const submit = async () => {
    const v = await form.validateFields()
    try {
      if (editing) await api.updateKnowledge(editing.name, { content: v.content })
      else await api.createKnowledge(v)
      message.success('已保存')
      setOpen(false)
      load()
    } catch (e: any) {
      message.error(e.response?.data?.message || '保存失败')
    }
  }

  return (
    <div style={{ maxWidth: 1100 }}>
      <Space style={{ marginBottom: 16 }} align="center">
        <Typography.Title level={4} style={{ margin: 0 }}>
          知识库
        </Typography.Title>
        <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>
          新建知识
        </Button>
      </Space>
      <Table
        rowKey="name"
        dataSource={items}
        pagination={false}
        onRow={(r) => ({ onClick: () => openEdit(r), style: { cursor: 'pointer' } })}
        columns={[
          { title: '名称', dataIndex: 'name' },
          {
            title: '类型',
            dataIndex: 'kind',
            render: (k) => <Tag color={k === 'menu' ? 'blue' : 'default'}>{k}</Tag>,
          },
          { title: '内容', dataIndex: 'content', ellipsis: true },
        ]}
      />
      <Modal
        title={editing ? '编辑知识' : '新建知识'}
        open={open}
        onOk={submit}
        onCancel={() => setOpen(false)}
        width={640}
      >
        <Form form={form} layout="vertical">
          <Form.Item name="name" label="名称" rules={[{ required: true, message: '请输入名称' }]}>
            <Input placeholder="如：餐厅菜单" disabled={!!editing} />
          </Form.Item>
          <Form.Item name="kind" label="类型" rules={[{ required: true, message: '请输入类型' }]}>
            <Input placeholder="menu / environment / profile" />
          </Form.Item>
          <Form.Item name="content" label="内容" rules={[{ required: true, message: '请输入内容' }]}>
            <Input.TextArea rows={10} placeholder="业务资料内容（文本或 JSON）" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}
