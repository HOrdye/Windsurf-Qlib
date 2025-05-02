import React, { useState, useEffect } from 'react';
import { Layout, Menu, Button, theme } from 'antd';
import {
  MenuFoldOutlined,
  MenuUnfoldOutlined,
  AppstoreOutlined,
  BarChartOutlined,
  SettingOutlined,
  CodeOutlined,
  DashboardOutlined,
  ApiOutlined,
  PlayCircleOutlined,
  ExperimentOutlined,
  BugOutlined
} from '@ant-design/icons';
import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom';
import DataPrefetcher, { createDefaultPrefetchRules } from './components/DataPrefetcher';
import { performanceMonitor } from './services/performanceService';
import CacheService from './services/cacheService';
import ConfigInitializer from './components/ConfigInitializer';

// 使用懒加载导入页面组件，并添加预加载功能
const Dashboard = (React as any).lazy(() => {
  // 记录组件加载开始时间
  const startTime = performance.now();
  return import('./pages/Dashboard').then(module => {
    // 记录组件加载耗时
    const loadTime = performance.now() - startTime;
    performanceMonitor.recordRenderTime('Dashboard-Load', loadTime);
    return module;
  });
});

// @ts-ignore - 忽略类型错误
const ConfigEditor = (React as any).lazy(() => {
  const startTime = performance.now();
  return import('./pages/ConfigEditor').then(module => {
    const loadTime = performance.now() - startTime;
    performanceMonitor.recordRenderTime('ConfigEditor-Load', loadTime);
    return module;
  });
});

// @ts-ignore - 忽略类型错误
const TaskMonitor = (React as any).lazy(() => {
  const startTime = performance.now();
  return import('./pages/TaskMonitor').then(module => {
    const loadTime = performance.now() - startTime;
    performanceMonitor.recordRenderTime('TaskMonitor-Load', loadTime);
    return module;
  });
});

// @ts-ignore - 忽略类型错误
const Visualization = (React as any).lazy(() => {
  const startTime = performance.now();
  return import('./pages/Visualization').then(module => {
    const loadTime = performance.now() - startTime;
    performanceMonitor.recordRenderTime('Visualization-Load', loadTime);
    return module;
  });
});

// @ts-ignore - 忽略类型错误
const Settings = (React as any).lazy(() => {
  const startTime = performance.now();
  return import('./pages/Settings').then(module => {
    const loadTime = performance.now() - startTime;
    performanceMonitor.recordRenderTime('Settings-Load', loadTime);
    return module;
  });
});

// @ts-ignore - 忽略类型错误
const WebSocketTest = (React as any).lazy(() => {
  const startTime = performance.now();
  return import('./pages/WebSocketTest').then(module => {
    const loadTime = performance.now() - startTime;
    performanceMonitor.recordRenderTime('WebSocketTest-Load', loadTime);
    return module;
  });
});

// @ts-ignore - 忽略类型错误
const TaskCenter = (React as any).lazy(() => {
  const startTime = performance.now();
  return import('./pages/TaskCenter').then(module => {
    const loadTime = performance.now() - startTime;
    performanceMonitor.recordRenderTime('TaskCenter-Load', loadTime);
    return module;
  });
});

// @ts-ignore - 忽略类型错误
const AlphaGenerator = (React as any).lazy(() => {
  const startTime = performance.now();
  return import('./pages/AlphaGenerator').then(module => {
    const loadTime = performance.now() - startTime;
    performanceMonitor.recordRenderTime('AlphaGenerator-Load', loadTime);
    return module;
  });
});

// @ts-ignore - 忽略类型错误
const ApiTest = (React as any).lazy(() => {
  const startTime = performance.now();
  return import('./pages/ApiTestPage').then(module => {
    const loadTime = performance.now() - startTime;
    performanceMonitor.recordRenderTime('ApiTestPage-Load', loadTime);
    return module;
  });
});

const { Header, Sider, Content } = Layout;

// 加载指示器组件
const LoadingComponent = () => (
  <div style={{ 
    display: 'flex', 
    justifyContent: 'center', 
    alignItems: 'center', 
    height: '100%',
    flexDirection: 'column'
  }}>
    <div style={{ fontSize: 24, marginBottom: 16 }}>加载中...</div>
  </div>
);

// 修复 React 18 类型问题
const App = () => {
  const [collapsed, setCollapsed] = useState(false);
  const { token } = theme.useToken();
  
  // 初始化性能监控
  useEffect(() => {
    // 每5分钟保存一次性能指标
    const metricsInterval = setInterval(() => {
      performanceMonitor.saveMetrics();
    }, 5 * 60 * 1000);
    
    // 恢复上次会话状态
    const lastSession = CacheService.getLastSession();
    if (lastSession && lastSession.collapsed !== undefined) {
      setCollapsed(lastSession.collapsed);
    }
    
    return () => {
      // 保存会话状态
      CacheService.saveLastSession({
        collapsed,
        lastVisit: Date.now()
      });
      
      // 清理资源
      clearInterval(metricsInterval);
    };
  }, [collapsed]);

  // 定义菜单项
  const menuItems = [
    {
      key: 'dashboard',
      icon: <DashboardOutlined />,
      label: <Link to="/">工作台</Link>
    },
    {
      key: 'config',
      icon: <CodeOutlined />,
      label: <Link to="/config">配置编辑</Link>
    },
    {
      key: 'task-center',
      icon: <PlayCircleOutlined />,
      label: <Link to="/task-center">任务中心</Link>
    },
    {
      key: 'tasks',
      icon: <AppstoreOutlined />,
      label: <Link to="/tasks">任务监控</Link>
    },
    {
      key: 'alpha-generator',
      icon: <ExperimentOutlined />,
      label: <Link to="/alpha-generator">Alpha因子生成器</Link>
    },
    {
      key: 'visualization',
      icon: <BarChartOutlined />,
      label: <Link to="/visualization">数据可视化</Link>
    },
    {
      key: 'settings',
      icon: <SettingOutlined />,
      label: <Link to="/settings">系统设置</Link>
    },
    {
      key: 'websocket-test',
      icon: <ApiOutlined />,
      label: <Link to="/websocket-test">WebSocket测试</Link>
    },
    {
      key: 'api-test',
      icon: <BugOutlined />,
      label: <Link to="/api-test">API测试</Link>
    }
  ];

  return (
    <Router>
      <ConfigInitializer />
      <DataPrefetcher rules={createDefaultPrefetchRules()}>
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
              Qlib量化平台
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
                {React.createElement(
                  (React as any).Suspense,
                  { fallback: <LoadingComponent /> },
                  <Routes>
                    <Route path="/" element={<Dashboard />} />
                    <Route path="/config" element={<ConfigEditor />} />
                    <Route path="/task-center" element={<TaskCenter />} />
                    <Route path="/tasks" element={<TaskMonitor />} />
                    <Route path="/visualization" element={<Visualization />} />
                    <Route path="/settings" element={<Settings />} />
                    <Route path="/websocket-test" element={<WebSocketTest />} />
                    <Route path="/alpha-generator" element={<AlphaGenerator />} />
                    <Route path="/api-test" element={<ApiTest />} />
                  </Routes>
                )}
              </Content>
            </Layout>
          </Layout>
        </Layout>
      </DataPrefetcher>
    </Router>
  );
};

export default App;
