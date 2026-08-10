import { useEffect, useState } from 'react'
import { Button, Empty, Space, message } from 'antd'
import { api } from '../../api/client'
import type { Datasource, Version } from '../../api/client'
import WorkflowCanvas from '../../editor/WorkflowCanvas'

export default function WorkflowTab({
  agentId,
  version,
  onChanged,
}: {
  agentId: string
  version: Version | null
  onChanged: () => void
}) {
  const [datasources, setDatasources] = useState<Datasource[]>([])
  useEffect(() => {
    api.listDatasources().then(setDatasources).catch(() => {})
  }, [])

  const startDraft = async () => {
    try {
      await api.createDraft(agentId)
      message.success('已创建草稿')
      onChanged()
    } catch (e: any) {
      message.error(e.response?.data?.message || '创建草稿失败')
    }
  }

  if (!version) return <Empty description="还没有版本，请先新建草稿" />

  const readOnly = version.status !== 'draft'

  return (
    <div>
      <Space style={{ marginBottom: 12 }}>
        <span>
          编辑版本：V{version.version_no}（{version.status === 'draft' ? '草稿' : '线上'}）
        </span>
        {readOnly && (
          <Button type="primary" size="small" onClick={startDraft}>
            新建草稿再编辑
          </Button>
        )}
      </Space>
      <WorkflowCanvas
        key={version.id}
        version={version}
        readOnly={readOnly}
        onSaved={onChanged}
        datasources={datasources}
      />
    </div>
  )
}
