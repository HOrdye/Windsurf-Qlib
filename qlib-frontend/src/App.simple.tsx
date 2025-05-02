/**
 * 简化版应用程序
 * 用于测试基本功能，避免类型错误
 */

import React from 'react';
import { Layout, Menu, Button, theme } from 'antd';
import {
  MenuFoldOutlined,
  MenuUnfoldOutlined,
  DashboardOutlined,
  SettingOutlined,
} from '@ant-design/icons';
import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom';

const { Header, Sider, Content } = Layout;

// 简单的仪表盘组件
const Dashboard = () => (
  <div style={{ padding: '20px' }}>
    <h1>Qlib量化平台 - 仪表盘</h1>
    <p>欢迎使用Qlib量化平台，这是一个简化版的仪表盘页面。</p>
  </div>
);

// 简单的设置组件
const Settings = () => (
  <div style={{ padding: '20px' }}>
    <h1>Qlib量化平台 - 设置</h1>
    <p>这是设置页面，您可以在这里配置系统参数。</p>
  </div>
);

// 简化版应用程序
const App = () => {
  const [collapsed, setCollapsed] = React.useState(false);
  const { token } = theme.useToken();

  // 定义菜单项
  const menuItems = [
    {
      key: 'dashboard',
      icon: <DashboardOutlined />,
      label: <Link to="/">仪表盘</Link>
    },
    {
      key: 'settings',
      icon: <SettingOutlined />,
      label: <Link to="/settings">设置</Link>
    }
  ];

  return (
    <Router>
      <Layout style={{ minHeight: '100vh' }}>
        <Header style={{
          position: 'sticky',
          top: 0,
          zIndex: 1,
          width: '100%',
          display: 'flex',
          alignItems: 'center',
          padding: '0 16px',
          background: token.colorBgContainer
        }}>
          <div style={{ fontSize: '18px', fontWeight: 'bold', marginRight: '20px' }}>
            Qlib量化平台 (简化版)
          </div>
          <Button
            type="text"
            icon={collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
            onClick={() => setCollapsed(!collapsed)}
            style={{ marginRight: '16px' }}
          />
        </Header>
        <Layout>
          <Sider width={250} collapsed={collapsed} style={{ background: token.colorBgContainer }}>
            <Menu
              mode="inline"
              defaultSelectedKeys={['dashboard']}
              style={{ height: '100%', borderRight: 0 }}
              items={menuItems}
            />
          </Sider>
          <Layout style={{ padding: '0 24px 24px' }}>
            <Content
              style={{
                padding: 24,
                margin: 0,
                minHeight: 280,
                background: token.colorBgContainer,
                borderRadius: token.borderRadiusLG,
              }}
            >
              <Routes>
                <Route path="/" element={<Dashboard />} />
                <Route path="/settings" element={<Settings />} />
              </Routes>
            </Content>
          </Layout>
        </Layout>
      </Layout>
    </Router>
  );
};

export default App;
