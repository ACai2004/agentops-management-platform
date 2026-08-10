import { useEffect, useState } from 'react'
import { Button, Form, Input, Modal, Popconfirm, Space, Table, Typography, message } from 'antd'
import { PlusOutlined } from '@ant-design/icons'
import { api } from '../api/client'
import type { Datasource } from '../api/client'

export default function DatasourceList() {
  const [items, setItems] = useState<Datasource[]>([])
  const [open, setOpen] = useState(false)
  const [form] = Form.useForm()

  const load = () => api.listDatasources().then(setItems).catch(() => message.error('加载失败'))
  useEffect(() => {
    load()
  }, [])

  const submit = async () => {
    const v = await form.validateFields()
    try {
      await api.createDatasource(v)
      message.success('已创建')
      setOpen(false)
      form.resetFields()
      load()
    } catch (e: any) {
      message.error(e.response?.data?.message || '创建失败')
    }
  }

  const remove = async (name: string) => {
    try {
      await api.deleteDatasource(name)
      message.success('已删除')
      load()
    } catch (e: any) {
      message.error(e.response?.data?.message || '删除失败')
    }
  }

  return (
    <div style={{ maxWidth: 1100 }}>
      <Space style={{ marginBottom: 16 }} align="center">
        <Typography.Title level={4} style={{ margin: 0 }}>
          数据源
        </Typography.Title>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => setOpen(true)}>
          新建数据源
        </Button>
      </Space>
      <Table
        rowKey="name"
        dataSource={items}
        pagination={false}
        columns={[
          { title: '名称', dataIndex: 'name' },
          { title: '地址', dataIndex: 'base_url', ellipsis: true },
          { title: '方式', dataIndex: 'method', width: 80 },
          { title: '类型', dataIndex: 'kind' },
          {
            title: '操作',
            render: (_, r) => (
              <Popconfirm title="确认删除？" onConfirm={() => remove(r.name)}>
                <Button type="link" danger size="small">
                  删除
                </Button>
              </Popconfirm>
            ),
          },
        ]}
      />
      <Modal title="新建数据源" open={open} onOk={submit} onCancel={() => setOpen(false)} width={560}>
        <Form form={form} layout="vertical">
          <Form.Item name="name" label="名称" rules={[{ required: true }]}>
            <Input placeholder="如：高德天气" />
          </Form.Item>
          <Form.Item name="base_url" label="接口地址" rules={[{ required: true }]}>
            <Input placeholder="含 key 的完整 URL（如 ?key=xxx）" />
          </Form.Item>
          <Form.Item name="method" label="请求方式" initialValue="GET">
            <Input placeholder="GET / POST" />
          </Form.Item>
          <Form.Item name="kind" label="类型">
            <Input placeholder="weather / ocr / vision 等" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}
