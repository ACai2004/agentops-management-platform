import { Layout, Menu } from 'antd'
import {
  ApiOutlined,
  AppstoreOutlined,
  BookOutlined,
  HomeOutlined,
} from '@ant-design/icons'
import { Link, Route, Routes, useLocation } from 'react-router-dom'
import AgentList from './pages/AgentList'
import AgentWorkspace from './pages/AgentWorkspace'
import CapabilityList from './pages/CapabilityList'
import DatasourceList from './pages/DatasourceList'
import KnowledgeList from './pages/KnowledgeList'

const { Sider, Content } = Layout

export default function App() {
  const location = useLocation()
  const selected = location.pathname.startsWith('/knowledge')
    ? 'knowledge'
    : location.pathname.startsWith('/capabilities')
      ? 'capabilities'
      : location.pathname.startsWith('/datasources')
        ? 'datasources'
        : 'agents'

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Sider
        theme="light"
        width={200}
        style={{ borderRight: '1px solid #f0f0f0' }}
      >
        <div style={{ padding: '16px 20px', fontWeight: 700, fontSize: 17, color: '#1677ff' }}>
          AgentOps
        </div>
        <Menu
          mode="inline"
          selectedKeys={[selected]}
          items={[
            { key: 'agents', icon: <HomeOutlined />, label: <Link to="/">Agent 列表</Link> },
            { key: 'knowledge', icon: <BookOutlined />, label: <Link to="/knowledge">知识库</Link> },
            { key: 'capabilities', icon: <AppstoreOutlined />, label: <Link to="/capabilities">能力</Link> },
            { key: 'datasources', icon: <ApiOutlined />, label: <Link to="/datasources">数据源</Link> },
          ]}
        />
      </Sider>
      <Content style={{ padding: 24, overflow: 'auto' }}>
        <Routes>
          <Route path="/" element={<AgentList />} />
          <Route path="/agents/:id/*" element={<AgentWorkspace />} />
          <Route path="/knowledge" element={<KnowledgeList />} />
          <Route path="/capabilities" element={<CapabilityList />} />
          <Route path="/datasources" element={<DatasourceList />} />
        </Routes>
      </Content>
    </Layout>
  )
}
