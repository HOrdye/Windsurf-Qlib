import React, { useState, useEffect } from 'react';
import { Layout, Menu, Card, Tabs, Typography, Button, Space, message, Row, Col } from 'antd';
import type { TabsProps } from 'antd';
import { 
  PlayCircleOutlined, 
  HistoryOutlined, 
  BarChartOutlined, 
  SettingOutlined,
  AppstoreOutlined,
  ReloadOutlined
} from '@ant-design/icons';
import WorkflowExecutor from '../components/WorkflowExecutor';
import WorkflowMonitor from '../components/WorkflowMonitor';
import TaskMonitor from '../components/TaskMonitor';
import DataVisualization from '../components/DataVisualization';
import WebSocketService from '../services/websocket';
import TaskManager from '../services/taskManager';

const { Header, Content, Sider } = Layout;
const { Title } = Typography;

const TaskCenter = () => {
  const [activeTab, setActiveTab] = useState<string>('workflow');
  const [selectedTaskId, setSelectedTaskId] = useState<string | null>(null);
  const [selectedWorkflowId, setSelectedWorkflowId] = useState<string | null>(null);
  const [wsConnected, setWsConnected] = useState<boolean>(false);
  
  useEffect(() => {
    const ws = WebSocketService.getInstance();
    
    const unsubscribe = ws.onConnectionChange((connected) => {
      setWsConnected(connected);
      if (connected) {
        message.success('已连接到Qlib服务器');
      } else {
        message.error('与Qlib服务器的连接已断开');
      }
    });
    
    if (!ws.isConnected()) {
      ws.connect();
    } else {
      setWsConnected(true);
    }
    
    return () => {
      unsubscribe();
    };
  }, []);
  
  const handleTaskSelect = (taskId: string) => {
    setSelectedTaskId(taskId);
    if (activeTab !== 'tasks') {
      setActiveTab('tasks');
    }
  };
  
  const handleWorkflowSelect = (workflowId: string) => {
    setSelectedWorkflowId(workflowId);
    if (activeTab !== 'workflows') {
      setActiveTab('workflows');
    }
  };
  
  const handleWorkflowStart = (workflowId: string) => {
    setSelectedWorkflowId(workflowId);
    setActiveTab('workflows');
    message.success('工作流已启动');
  };
  
  const handleReconnect = () => {
    const ws = WebSocketService.getInstance();
    ws.connect();
  };
  
  const renderHeader = () => (
    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
      <Title level={2}>任务中心</Title>
      <Space>
        <Button 
          type={wsConnected ? 'default' : 'primary'}
          icon={<ReloadOutlined />}
          onClick={handleReconnect}
          disabled={wsConnected}
        >
          {wsConnected ? '已连接' : '重新连接'}
        </Button>
      </Space>
    </div>
  );
  
  const renderContent = () => {
    // 定义标签页内容
    const items = [
      {
        key: 'workflow',
        label: (
          <span>
            <PlayCircleOutlined />
            工作流执行
          </span>
        ),
        children: (
          <Row gutter={[16, 16]}>
            <Col span={24}>
              <WorkflowExecutor onWorkflowStart={handleWorkflowStart} />
            </Col>
          </Row>
        )
      },
      {
        key: 'workflows',
        label: (
          <span>
            <HistoryOutlined />
            工作流监控
          </span>
        ),
        children: (
          <WorkflowMonitor 
            height="calc(100vh - 230px)"
            workflowId={selectedWorkflowId || undefined}
            onWorkflowSelect={handleWorkflowSelect}
          />
        )
      },
      {
        key: 'tasks',
        label: (
          <span>
            <AppstoreOutlined />
            任务监控
          </span>
        ),
        children: (
          <TaskMonitor
            height="calc(100vh - 230px)"
            selectedTaskId={selectedTaskId || undefined}
            onTaskSelect={handleTaskSelect}
          />
        )
      },
      {
        key: 'visualization',
        label: (
          <span>
            <BarChartOutlined />
            数据可视化
          </span>
        ),
        children: (
          <DataVisualization
            height="calc(100vh - 230px)"
            taskId={selectedTaskId || undefined}
          />
        )
      }
    ];
    
    return (
      <Tabs activeKey={activeTab} onChange={setActiveTab} size="large" items={items} />
    );
  };
  
  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Content style={{ padding: '24px' }}>
        {renderHeader()}
        {renderContent()}
      </Content>
    </Layout>
  );
};

export default TaskCenter;
