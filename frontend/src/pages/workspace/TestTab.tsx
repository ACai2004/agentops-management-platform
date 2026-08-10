import { useState } from 'react'
import { Button, Card, Input, Space, Tag, Timeline, Typography, Upload, message } from 'antd'
import { UploadOutlined } from '@ant-design/icons'
import { api } from '../../api/client'
import type { Trace, Version } from '../../api/client'

export default function TestTab({ agentId, version }: { agentId: string; version: Version | null }) {
  const [input, setInput] = useState('')
  const [image, setImage] = useState<string>()
  const [running, setRunning] = useState(false)
  const [trace, setTrace] = useState<Trace | null>(null)

  const run = async () => {
    if (!input.trim()) return message.warning('请输入测试内容')
    if (!version) return message.warning('请先创建版本')
    setRunning(true)
    try {
      const t = await api.run(agentId, { input, image_url: image, version_id: version.id, env: 'test' })
      setTrace(t)
    } catch (e: any) {
      message.error(e.response?.data?.message || '运行失败')
    } finally {
      setRunning(false)
    }
  }

  const onFile = (file: File) => {
    const reader = new FileReader()
    reader.onload = () => setImage(reader.result as string)
    reader.readAsDataURL(file)
    return false
  }

  const renderOutput = (v: unknown) =>
    typeof v === 'string' ? v : JSON.stringify(v, null, 2)

  return (
    <div style={{ maxWidth: 760 }}>
      <Card>
        <Input.TextArea
          rows={3}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="输入测试内容，如：我和朋友两个人第一次来这家店"
        />
        <Space style={{ marginTop: 12 }}>
          <Upload beforeUpload={onFile} showUploadList={false} accept="image/*">
            <Button icon={<UploadOutlined />}>{image ? '重新选择图片' : '上传图片（小票）'}</Button>
          </Upload>
          {image && (
            <Button size="small" onClick={() => setImage(undefined)}>
              移除图片
            </Button>
          )}
          <Button type="primary" loading={running} onClick={run}>
            运行
          </Button>
        </Space>
        {image && (
          <div style={{ marginTop: 8 }}>
            <img src={image} alt="小票" style={{ maxWidth: 220, maxHeight: 220, borderRadius: 8, border: '1px solid #f0f0f0' }} />
          </div>
        )}
      </Card>

      {trace && (
        <Card title="运行结果" style={{ marginTop: 16 }}>
          <Typography.Paragraph>
            <b>回复：</b>
            {trace.output}
          </Typography.Paragraph>
          <Typography.Title level={5}>Trace 步骤</Typography.Title>
          <Timeline
            items={trace.steps.map((s, i) => ({
              key: i,
              color:
                s.node_type === 'http' ? 'green' : s.node_type === 'decision' ? 'orange' : 'blue',
              content: (
                <div>
                  <b>{s.node_id}</b> <Tag>{s.node_type}</Tag>
                  {s.branch && <Tag color="purple">→ {s.branch}</Tag>}
                  <div style={{ color: '#666', fontSize: 12, whiteSpace: 'pre-wrap' }}>
                    {renderOutput(s.output)}
                  </div>
                </div>
              ),
            }))}
          />
        </Card>
      )}
    </div>
  )
}
