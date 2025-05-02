import React, { useState, useEffect } from 'react';
import { Card, Table, Tag, Button, Space, Progress, Typography, Tabs, Badge, Descriptions, Collapse } from 'antd';
import { 
  PlayCircleOutlined, 
  PauseCircleOutlined, 
  StopOutlined,
  ReloadOutlined,
  FileTextOutlined,
  CodeOutlined,
  DownOutlined
} from '@ant-design/icons';

const { Title, Text } = Typography;
const { TabPane } = Tabs;
const { Panel } = Collapse;

// 任务状态类型
type TaskStatus = 'running' | 'success' | 'failed' | 'pending';

// 任务类型接口
interface Task {
  id: string;
  name: string;
  status: TaskStatus;
  progress: number;
  startTime: Date;
  endTime?: Date;
  type: 'training' | 'backtest' | 'data_init';
  log: string[];
}

// 模拟任务数据
const mockTasks: Task[] = [
  {
    id: '1',
    name: 'CSI300 LGBM训练',
    status: 'success',
    progress: 100,
    startTime: new Date(2025, 3, 2, 10, 15),
    endTime: new Date(2025, 3, 2, 10, 45),
    type: 'training',
    log: [
      '[10:15:32] 任务开始...',
      '[10:16:10] 数据加载完成',
      '[10:16:45] 开始特征计算...',
      '[10:25:20] 特征计算完成',
      '[10:25:30] 开始模型训练...',
      '[10:40:15] 模型训练完成，AUC: 0.587',
      '[10:45:00] 任务完成'
    ]
  },
  {
    id: '2',
    name: 'CSI300 回测分析',
    status: 'running',
    progress: 65,
    startTime: new Date(2025, 3, 3, 9, 5),
    type: 'backtest',
    log: [
      '[09:05:10] 任务开始...',
      '[09:05:45] 加载模型...',
      '[09:06:30] 模型加载完成',
      '[09:07:15] 开始回测...',
      '[09:20:30] 回测计算中...',
    ]
  },
  {
    id: '3',
    name: '数据初始化',
    status: 'pending',
    progress: 0,
    startTime: new Date(2025, 3, 3, 11, 0),
    type: 'data_init',
    log: []
  }
];

// 修改组件类型定义，避免使用 React.FC
const TaskMonitor = (): JSX.Element => {
  const [tasks, setTasks] = useState<Task[]>(mockTasks);
  const [selectedTask, setSelectedTask] = useState<Task | null>(null);
  
  // 模拟任务进度更新
  useEffect(() => {
    const timer = setInterval(() => {
      setTasks(prev => {
        return prev.map(task => {
          if (task.status === 'running' && task.progress < 100) {
            const newProgress = Math.min(task.progress + 1, 100);
            
            // 如果进度达到100，则完成任务
            if (newProgress === 100) {
              return { 
                ...task, 
                progress: newProgress, 
                status: 'success',
                endTime: new Date(),
                log: [...task.log, `[${new Date().toLocaleTimeString()}] 任务完成`]
              };
            }
            
            // 否则继续进行
            return { 
              ...task, 
              progress: newProgress,
              log: task.progress % 10 === 0 
                ? [...task.log, `[${new Date().toLocaleTimeString()}] 进度更新: ${newProgress}%`]
                : task.log
            };
          }
          return task;
        });
      });
    }, 3000);

    return () => clearInterval(timer);
  }, []);

  // 根据任务状态获取颜色
  const getStatusColor = (status: TaskStatus) => {
    const statusMap: Record<TaskStatus, string> = {
      'running': 'processing',
      'success': 'success',
      'failed': 'error',
      'pending': 'default'
    };
    return statusMap[status];
  };

  // 获取任务类型标签
  const getTaskTypeTag = (type: string) => {
    const typeColorMap: Record<string, string> = {
      'training': 'blue',
      'backtest': 'green',
      'data_init': 'orange'
    };
    
    const typeNameMap: Record<string, string> = {
      'training': '模型训练',
      'backtest': '策略回测',
      'data_init': '数据初始化'
    };
    
    return <Tag color={typeColorMap[type]}>{typeNameMap[type]}</Tag>;
  };

  // 表格列定义
  const columns = [
    {
      title: '任务名称',
      dataIndex: 'name',
      key: 'name',
    },
    {
      title: '类型',
      dataIndex: 'type',
      key: 'type',
      render: (type: string) => getTaskTypeTag(type)
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status: TaskStatus) => (
        <Badge status={getStatusColor(status) as any} text={
          status === 'running' ? '运行中' :
          status === 'success' ? '已完成' :
          status === 'failed' ? '失败' : '等待中'
        } />
      )
    },
    {
      title: '进度',
      dataIndex: 'progress',
      key: 'progress',
      render: (progress: number) => <Progress percent={progress} size="small" />
    },
    {
      title: '开始时间',
      dataIndex: 'startTime',
      key: 'startTime',
      render: (date: Date) => date.toLocaleString()
    },
    {
      title: '操作',
      key: 'action',
      render: (_: any, record: Task) => (
        <Space size="small">
          {record.status === 'running' && (
            <Button type="text" icon={<PauseCircleOutlined />} size="small">
              暂停
            </Button>
          )}
          {record.status === 'pending' && (
            <Button type="text" icon={<PlayCircleOutlined />} size="small">
              启动
            </Button>
          )}
          <Button 
            type="text" 
            icon={<FileTextOutlined />} 
            size="small"
            onClick={() => setSelectedTask(record)}
          >
            详情
          </Button>
        </Space>
      ),
    },
  ];

  return (
    <div>
      <Card 
        title="任务监控" 
        bordered={false}
        extra={
          <Space>
            <Button icon={<ReloadOutlined />}>刷新</Button>
            <Button icon={<PlayCircleOutlined />} type="primary">新建任务</Button>
          </Space>
        }
      >
        <Tabs defaultActiveKey="all">
          <TabPane tab="全部任务" key="all">
            <Table 
              dataSource={tasks} 
              columns={columns} 
              rowKey="id"
              pagination={false}
              onRow={(record) => {
                return {
                  onClick: () => setSelectedTask(record)
                };
              }}
            />
          </TabPane>
          <TabPane tab="运行中" key="running">
            <Table 
              dataSource={tasks.filter(t => t.status === 'running')} 
              columns={columns} 
              rowKey="id"
              pagination={false}
            />
          </TabPane>
          <TabPane tab="已完成" key="completed">
            <Table 
              dataSource={tasks.filter(t => t.status === 'success')} 
              columns={columns} 
              rowKey="id" 
              pagination={false}
            />
          </TabPane>
        </Tabs>
        
        {selectedTask && (
          <Card
            title={`任务详情：${selectedTask.name}`}
            style={{ marginTop: 16 }}
            extra={
              <Button type="text" icon={<DownOutlined />}>
                导出日志
              </Button>
            }
          >
            <Descriptions bordered size="small" column={2}>
              <Descriptions.Item label="任务ID">{selectedTask.id}</Descriptions.Item>
              <Descriptions.Item label="类型">{getTaskTypeTag(selectedTask.type)}</Descriptions.Item>
              <Descriptions.Item label="状态">
                <Badge 
                  status={getStatusColor(selectedTask.status) as any} 
                  text={
                    selectedTask.status === 'running' ? '运行中' :
                    selectedTask.status === 'success' ? '已完成' :
                    selectedTask.status === 'failed' ? '失败' : '等待中'
                  } 
                />
              </Descriptions.Item>
              <Descriptions.Item label="进度">
                <Progress percent={selectedTask.progress} />
              </Descriptions.Item>
              <Descriptions.Item label="开始时间">
                {selectedTask.startTime.toLocaleString()}
              </Descriptions.Item>
              <Descriptions.Item label="结束时间">
                {selectedTask.endTime ? selectedTask.endTime.toLocaleString() : '-'}
              </Descriptions.Item>
            </Descriptions>
            
            <Collapse defaultActiveKey={['logs']} style={{ marginTop: 16 }}>
              <Panel header="任务日志" key="logs">
                <div 
                  style={{ 
                    backgroundColor: '#f0f0f0', 
                    padding: 10, 
                    maxHeight: 300, 
                    overflow: 'auto',
                    fontFamily: 'monospace'
                  }}
                >
                  {selectedTask.log.length > 0 ? (
                    selectedTask.log.map((line, index) => (
                      <div key={index}>{line}</div>
                    ))
                  ) : (
                    <Text type="secondary">暂无日志记录</Text>
                  )}
                </div>
              </Panel>
              <Panel header="配置信息" key="config">
                <pre>{`任务配置信息将显示在这里...`}</pre>
              </Panel>
            </Collapse>
          </Card>
        )}
      </Card>
    </div>
  );
};

export default TaskMonitor;
