import React, { useState, useEffect } from 'react';
import { Card, Row, Col, Statistic, Button, Space, Alert, Progress, List, Typography, Tag, Empty, Spin, Tabs, Timeline } from 'antd';
import { 
  PlayCircleOutlined, 
  FileTextOutlined, 
  LineChartOutlined, 
  DatabaseOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  SyncOutlined,
  RocketOutlined,
  AreaChartOutlined,
  SettingOutlined,
  ClockCircleOutlined
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { useSettingsStore } from '../store/settingsStore';
import { useConfigStore } from '../store/configStore';
import { useTaskStore } from '../store/taskStore';
import PageLayout from '../components/PageLayout';

const { Title, Text } = Typography;
const { TabPane } = Tabs;

// 修改组件类型定义，显式指定返回类型
const Dashboard = () => {
  const navigate = useNavigate();
  const { server } = useSettingsStore();
  const { configs = [] } = useConfigStore();
  const { tasks = [], fetchTasks } = useTaskStore();
  
  const [isServerConnected, setIsServerConnected] = useState<boolean>(false);
  const [systemStats, setSystemStats] = useState({
    cpuUsage: 0,
    memoryUsage: 0,
    diskUsage: 0,
    uptime: 0
  });
  const [isLoading, setIsLoading] = useState<boolean>(true);
  
  // 模拟获取系统状态数据
  useEffect(() => {
    const fetchSystemStats = async () => {
      setIsLoading(true);
      
      try {
        // 实际项目中，这里应调用API获取数据
        // const response = await qlibApi.getSystemStats();
        // setSystemStats(response.data);
        
        // 模拟数据
        setTimeout(() => {
          setSystemStats({
            cpuUsage: Math.floor(Math.random() * 60) + 10,
            memoryUsage: Math.floor(Math.random() * 50) + 20,
            diskUsage: Math.floor(Math.random() * 30) + 10,
            uptime: Math.floor(Math.random() * 1000) + 100
          });
          
          setIsServerConnected(true);
          setIsLoading(false);
        }, 1000);
        
        // 模拟获取任务数据
        if (fetchTasks) {
          fetchTasks();
        }
      } catch (error) {
        console.error('获取系统状态失败:', error);
        setIsServerConnected(false);
        setIsLoading(false);
      }
    };
    
    fetchSystemStats();
    
    // 定期刷新系统状态
    const intervalId = setInterval(fetchSystemStats, 30000);
    
    return () => clearInterval(intervalId);
  }, [fetchTasks]);
  
  // 获取最近任务
  const getRecentTasks = () => {
    if (!tasks || !Array.isArray(tasks) || tasks.length === 0) {
      return [];
    }
    return [...tasks].slice(0, 5).sort((a, b) => {
      const dateA = a.startTime ? new Date(a.startTime).getTime() : 0;
      const dateB = b.startTime ? new Date(b.startTime).getTime() : 0;
      return dateB - dateA;
    });
  };
  
  // 获取常用配置
  const getFrequentConfigs = () => {
    if (!configs || !Array.isArray(configs) || configs.length === 0) {
      return [];
    }
    return [...configs]
      .filter(config => config && typeof config === 'object')
      .sort((a, b) => {
        const usageCountA = a.usageCount || 0;
        const usageCountB = b.usageCount || 0;
        return usageCountB - usageCountA;
      })
      .slice(0, 5);
  };
  
  // 获取任务状态统计
  const getTaskStats = () => {
    if (!tasks || !Array.isArray(tasks)) {
      return { runningTasks: 0, completedTasks: 0, failedTasks: 0, pendingTasks: 0 };
    }
    
    const runningTasks = tasks.filter(task => task && task.status === 'running').length;
    const completedTasks = tasks.filter(task => task && task.status === 'success').length;
    const failedTasks = tasks.filter(task => task && task.status === 'failed').length;
    const pendingTasks = tasks.filter(task => task && task.status === 'pending').length;
    
    return { runningTasks, completedTasks, failedTasks, pendingTasks };
  };
  
  // 获取最近活动
  const getRecentActivities = () => {
    // 实际项目中，这里应该从API获取数据
    return [
      { id: '1', type: 'task', action: '完成', name: 'LGBM模型训练', time: '10分钟前' },
      { id: '2', type: 'config', action: '编辑', name: 'Alpha158配置', time: '30分钟前' },
      { id: '3', type: 'task', action: '开始', name: '策略回测', time: '2小时前' },
      { id: '4', type: 'system', action: '更新', name: 'Qlib库', time: '1天前' },
      { id: '5', type: 'config', action: '创建', name: '新策略配置', time: '2天前' }
    ];
  };
  
  // 格式化系统运行时间
  const formatUptime = (seconds: number) => {
    const days = Math.floor(seconds / (3600 * 24));
    const hours = Math.floor((seconds % (3600 * 24)) / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    
    return `${days}天 ${hours}小时 ${minutes}分钟`;
  };
  
  // 获取活动图标
  const getActivityIcon = (type: string, action: string) => {
    if (type === 'task') {
      if (action === '完成') return <CheckCircleOutlined style={{ color: '#52c41a' }} />;
      if (action === '失败') return <CloseCircleOutlined style={{ color: '#f5222d' }} />;
      if (action === '开始') return <PlayCircleOutlined style={{ color: '#1890ff' }} />;
      return <SyncOutlined style={{ color: '#faad14' }} />;
    }
    
    if (type === 'config') {
      if (action === '创建') return <FileTextOutlined style={{ color: '#1890ff' }} />;
      if (action === '编辑') return <SettingOutlined style={{ color: '#722ed1' }} />;
      return <FileTextOutlined style={{ color: '#1890ff' }} />;
    }
    
    return <RocketOutlined style={{ color: '#faad14' }} />;
  };
  
  const recentTasks = getRecentTasks();
  const frequentConfigs = getFrequentConfigs();
  const taskStats = getTaskStats();
  
  return (
    <PageLayout>
      <div style={{ padding: '24px' }}>
        <Row gutter={[16, 16]}>
          {/* 系统状态卡片 */}
          <Col span={24}>
            <Card bordered={false}>
              <Spin spinning={isLoading}>
                {isServerConnected ? (
                  <Row gutter={[16, 16]}>
                    <Col span={6}>
                      <Statistic 
                        title="CPU使用率" 
                        value={systemStats.cpuUsage} 
                        suffix="%" 
                        precision={1}
                      />
                      <Progress 
                        percent={systemStats.cpuUsage} 
                        status={systemStats.cpuUsage > 80 ? "exception" : "normal"}
                        showInfo={false}
                      />
                    </Col>
                    <Col span={6}>
                      <Statistic 
                        title="内存使用率" 
                        value={systemStats.memoryUsage} 
                        suffix="%" 
                        precision={1}
                      />
                      <Progress 
                        percent={systemStats.memoryUsage} 
                        status={systemStats.memoryUsage > 80 ? "exception" : "normal"}
                        showInfo={false}
                      />
                    </Col>
                    <Col span={6}>
                      <Statistic 
                        title="磁盘使用率" 
                        value={systemStats.diskUsage} 
                        suffix="%" 
                        precision={1}
                      />
                      <Progress 
                        percent={systemStats.diskUsage} 
                        status={systemStats.diskUsage > 80 ? "exception" : "normal"}
                        showInfo={false}
                      />
                    </Col>
                    <Col span={6}>
                      <Statistic 
                        title="系统运行时间" 
                        value={formatUptime(systemStats.uptime)} 
                        valueStyle={{ fontSize: '14px' }}
                      />
                    </Col>
                  </Row>
                ) : (
                  <Alert
                    message="服务器连接失败"
                    description="无法连接到Qlib服务器，请检查网络连接或服务器状态。"
                    type="error"
                    showIcon
                    action={
                      <Button size="small" danger>
                        重试连接
                      </Button>
                    }
                  />
                )}
              </Spin>
            </Card>
          </Col>
          
          {/* 任务统计卡片 */}
          <Col span={24}>
            <Card title="任务统计" bordered={false}>
              <Row gutter={[16, 16]}>
                <Col span={6}>
                  <Card>
                    <Statistic
                      title="运行中任务"
                      value={taskStats.runningTasks}
                      valueStyle={{ color: '#1890ff' }}
                      prefix={<SyncOutlined spin />}
                    />
                  </Card>
                </Col>
                <Col span={6}>
                  <Card>
                    <Statistic
                      title="已完成任务"
                      value={taskStats.completedTasks}
                      valueStyle={{ color: '#52c41a' }}
                      prefix={<CheckCircleOutlined />}
                    />
                  </Card>
                </Col>
                <Col span={6}>
                  <Card>
                    <Statistic
                      title="失败任务"
                      value={taskStats.failedTasks}
                      valueStyle={{ color: '#f5222d' }}
                      prefix={<CloseCircleOutlined />}
                    />
                  </Card>
                </Col>
                <Col span={6}>
                  <Card>
                    <Statistic
                      title="等待中任务"
                      value={taskStats.pendingTasks}
                      valueStyle={{ color: '#faad14' }}
                      prefix={<ClockCircleOutlined />}
                    />
                  </Card>
                </Col>
              </Row>
            </Card>
          </Col>
          
          {/* 快速操作卡片 */}
          <Col span={24}>
            <Card title="快速操作" bordered={false}>
              <Space size="middle">
                <Button 
                  type="primary" 
                  icon={<PlayCircleOutlined />}
                  onClick={() => navigate('/task-center')}
                >
                  执行工作流
                </Button>
                <Button 
                  icon={<FileTextOutlined />}
                  onClick={() => navigate('/config')}
                >
                  管理配置
                </Button>
                <Button 
                  icon={<LineChartOutlined />}
                  onClick={() => navigate('/visualization')}
                >
                  查看分析
                </Button>
                <Button 
                  icon={<DatabaseOutlined />}
                  onClick={() => navigate('/data')}
                >
                  数据管理
                </Button>
              </Space>
            </Card>
          </Col>
          
          {/* 最近任务和常用配置卡片 */}
          <Col span={24}>
            <Card bordered={false}>
              <Tabs defaultActiveKey="tasks">
                <TabPane 
                  tab={<span><SyncOutlined />最近任务</span>}
                  key="tasks"
                >
                  {recentTasks.length > 0 ? (
                    <List
                      dataSource={recentTasks}
                      renderItem={task => (
                        <List.Item
                          actions={[
                            <Button 
                              type="link" 
                              onClick={() => navigate(`/task?id=${task.id}`)}
                            >
                              查看详情
                            </Button>
                          ]}
                        >
                          <List.Item.Meta
                            title={task.name}
                            description={
                              <div>
                                <div>
                                  <Tag color={
                                    task.status === 'success' ? 'success' : 
                                    task.status === 'failed' ? 'error' : 
                                    task.status === 'running' ? 'processing' : 'default'
                                  }>
                                    {task.status === 'success' ? '已完成' : 
                                     task.status === 'failed' ? '失败' : 
                                     task.status === 'running' ? '运行中' : '等待中'}
                                  </Tag>
                                  <Text type="secondary" style={{ marginLeft: 8 }}>
                                    {task.startTime ? new Date(task.startTime).toLocaleString() : '未开始'}
                                  </Text>
                                </div>
                                {task.status === 'running' && (
                                  <Progress 
                                    percent={task.progress || 0} 
                                    size="small" 
                                    status="active" 
                                    style={{ marginTop: 8 }}
                                  />
                                )}
                              </div>
                            }
                          />
                        </List.Item>
                      )}
                    />
                  ) : (
                    <Empty description="暂无任务记录" image={Empty.PRESENTED_IMAGE_SIMPLE} />
                  )}
                </TabPane>
                
                <TabPane 
                  tab={<span><FileTextOutlined />常用配置</span>}
                  key="configs"
                >
                  {frequentConfigs.length > 0 ? (
                    <List
                      dataSource={frequentConfigs}
                      renderItem={config => (
                        <List.Item
                          actions={[
                            <Button 
                              type="link" 
                              onClick={() => navigate(`/config?id=${config.id}`)}
                            >
                              编辑
                            </Button>,
                            <Button 
                              type="link" 
                              onClick={() => navigate(`/task/new?configId=${config.id}`)}
                            >
                              创建任务
                            </Button>
                          ]}
                        >
                          <List.Item.Meta
                            avatar={<FileTextOutlined />}
                            title={config.name}
                            description={
                              <div>
                                <Text type="secondary" ellipsis={{ tooltip: config.description }}>
                                  {config.description || '无描述'}
                                </Text>
                                <div style={{ marginTop: 4 }}>
                                  <Tag color="blue">{config.type}</Tag>
                                  {config.isDefault && <Tag color="gold">默认</Tag>}
                                </div>
                              </div>
                            }
                          />
                        </List.Item>
                      )}
                    />
                  ) : (
                    <Empty description="暂无配置" image={Empty.PRESENTED_IMAGE_SIMPLE} />
                  )}
                </TabPane>
                
                <TabPane 
                  tab={<span><AreaChartOutlined />性能指标</span>}
                  key="metrics"
                >
                  {/* 这里可以根据需要显示性能指标 */}
                  <Empty description="暂无性能指标数据" image={Empty.PRESENTED_IMAGE_SIMPLE} />
                </TabPane>
              </Tabs>
            </Card>
          </Col>
          
          {/* 最近活动卡片 */}
          <Col span={24}>
            <Card title="最近活动" bordered={false}>
              <Timeline>
                {getRecentActivities().map(activity => (
                  <Timeline.Item
                    key={activity.id}
                    dot={getActivityIcon(activity.type, activity.action)}
                  >
                    <Text strong>
                      {activity.action}了{activity.type === 'task' ? '任务' : 
                                          activity.type === 'config' ? '配置' : '系统组件'}
                    </Text>：{activity.name}
                    <div>
                      <Text type="secondary">{activity.time}</Text>
                    </div>
                  </Timeline.Item>
                ))}
              </Timeline>
            </Card>
          </Col>
        </Row>
      </div>
    </PageLayout>
  );
};

export default Dashboard;
