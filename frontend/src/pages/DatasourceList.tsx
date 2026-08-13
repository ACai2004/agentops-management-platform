import { useEffect, useState } from 'react'
import { Button, Form, Input, Modal, Popconfirm, Select, Space, Switch, Table, Typography, message } from 'antd'
import { DeleteOutlined, EditOutlined, PlusOutlined } from '@ant-design/icons'
import { api } from '../api/client'
import type { Datasource } from '../api/client'

const PARAM_TYPE_OPTIONS = [
  { value: 'text', label: '文本' },
  { value: 'number', label: '数字' },
  { value: 'select', label: '下拉' },
]

export default function DatasourceList() {
  const [items, setItems] = useState<Datasource[]>([])
  const [open, setOpen] = useState(false)
  const [editing, setEditing] = useState<Datasource | null>(null)
  const [form] = Form.useForm()

  const load = () => api.listDatasources().then(setItems).catch(() => message.error('加载失败'))
  useEffect(() => {
    load()
  }, [])

  const openCreate = () => {
    setEditing(null)
    form.resetFields()
    form.setFieldsValue({ method: 'GET', param_defs: [] })
    setOpen(true)
  }
  const openEdit = (d: Datasource) => {
    setEditing(d)
    form.setFieldsValue({
      name: d.name,
      base_url: d.base_url,
      method: d.method,
      kind: d.kind,
      param_defs: (d.param_defs || []).map((p) => ({
        name: p.name,
        label: p.label || '',
        required: !!p.required,
        type: p.type || 'text',
        options: (p.options || []).join(','),
        placeholder: p.placeholder || '',
      })),
    })
    setOpen(true)
  }

  const submit = async () => {
    const v = await form.validateFields()
    const param_defs = (v.param_defs || []).map((p: any) => ({
      name: p.name,
      label: p.label,
      required: !!p.required,
      type: p.type || 'text',
      options: p.type === 'select' ? (p.options || '').split(',').map((s: string) => s.trim()).filter(Boolean) : [],
      placeholder: p.placeholder,
    }))
    try {
      if (editing) {
        await api.updateDatasource(editing.name, { base_url: v.base_url, method: v.method, kind: v.kind, param_defs })
      } else {
        await api.createDatasource({ name: v.name, base_url: v.base_url, method: v.method, kind: v.kind, param_defs })
      }
      message.success('已保存')
      setOpen(false)
      load()
    } catch (e: any) {
      message.error(e.response?.data?.message || '保存失败')
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
        <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>
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
            title: '参数',
            render: (_, r) =>
              (r.param_defs || []).map((p) => `${p.label || p.name}${p.required ? '(必填)' : ''}`).join('、') || '—',
          },
          {
            title: '操作',
            render: (_, r) => (
              <Space>
                <Button type="link" size="small" icon={<EditOutlined />} onClick={() => openEdit(r)}>
                  编辑
                </Button>
                <Popconfirm title="确认删除？" onConfirm={() => remove(r.name)}>
                  <Button type="link" danger size="small">
                    删除
                  </Button>
                </Popconfirm>
              </Space>
            ),
          },
        ]}
      />
      <Modal title={editing ? '编辑数据源' : '新建数据源'} open={open} onOk={submit} onCancel={() => setOpen(false)} width={680}>
        <Form form={form} layout="vertical">
          <Form.Item name="name" label="名称" rules={[{ required: true, message: '请输入名称' }]}>
            <Input placeholder="如：高德天气" disabled={!!editing} />
          </Form.Item>
          <Form.Item name="base_url" label="接口地址" rules={[{ required: true, message: '请输入接口地址' }]}>
            <Input placeholder="接口地址（不含 key，如 https://restapi.amap.com/v3/weather/weatherInfo）" />
          </Form.Item>
          <Form.Item name="method" label="请求方式" initialValue="GET">
            <Input placeholder="GET / POST" />
          </Form.Item>
          <Form.Item name="kind" label="类型">
            <Input placeholder="weather / ocr / vision 等" />
          </Form.Item>

          <Typography.Text strong>参数定义</Typography.Text>
          <Typography.Paragraph type="secondary" style={{ fontSize: 12, marginBottom: 8 }}>
            声明这个接口需要填哪些参数；「获取数据」节点选择本数据源后，会按此渲染成表单，业务人员只填值、不用知道参数名。
          </Typography.Paragraph>
          <Form.List name="param_defs">
            {(fields, { add, remove: removeField }) => (
              <>
                {fields.map((f) => (
                  <div key={f.key} style={{ border: '1px solid #f0f0f0', borderRadius: 6, padding: 8, marginBottom: 8 }}>
                    <Space wrap style={{ display: 'flex' }}>
                      <Form.Item name={[f.name, 'label']} style={{ marginBottom: 4 }}>
                        <Input size="small" placeholder="中文名（如 城市编码）" style={{ width: 116 }} />
                      </Form.Item>
                      <Form.Item name={[f.name, 'name']} style={{ marginBottom: 4 }} rules={[{ required: true, message: '参数名必填' }]}>
                        <Input size="small" placeholder="参数名（如 city）" style={{ width: 104 }} />
                      </Form.Item>
                      <Form.Item name={[f.name, 'type']} style={{ marginBottom: 4 }}>
                        <Select size="small" style={{ width: 80 }} options={PARAM_TYPE_OPTIONS} />
                      </Form.Item>
                      <Form.Item name={[f.name, 'required']} valuePropName="checked" style={{ marginBottom: 4 }}>
                        <Switch size="small" />
                      </Form.Item>
                      <Typography.Text style={{ fontSize: 12 }}>必填</Typography.Text>
                      <Button type="text" danger size="small" icon={<DeleteOutlined />} onClick={() => removeField(f.name)} />
                    </Space>
                    <Form.Item noStyle shouldUpdate={(p, q) => p.param_defs?.[f.name]?.type !== q.param_defs?.[f.name]?.type}>
                      {({ getFieldValue }) =>
                        getFieldValue(['param_defs', f.name, 'type']) === 'select' ? (
                          <Form.Item name={[f.name, 'options']} style={{ marginBottom: 4 }}>
                            <Input size="small" placeholder="下拉选项，用逗号分隔（如 base, all）" />
                          </Form.Item>
                        ) : null
                      }
                    </Form.Item>
                    <Form.Item name={[f.name, 'placeholder']} style={{ marginBottom: 0 }}>
                      <Input size="small" placeholder="占位提示（可选，如：如 110105 或 {{adcode}}）" />
                    </Form.Item>
                  </div>
                ))}
                <Button
                  type="dashed" block icon={<PlusOutlined />}
                  onClick={() => add({ name: '', label: '', required: false, type: 'text', options: '', placeholder: '' })}
                >
                  添加参数
                </Button>
              </>
            )}
          </Form.List>
        </Form>
      </Modal>
    </div>
  )
}
