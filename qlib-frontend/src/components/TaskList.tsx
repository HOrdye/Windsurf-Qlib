import React, { useState } from 'react';
import { 
  Card, List, Tag, Button, Input, Space, 
  Popconfirm, Typography, Empty, Tooltip, 
  Badge, Progress, Dropdown
} from 'antd';
import { 
  SearchOutlined, 
  DeleteOutlined, 
  EyeOutlined,
  FilterOutlined,
  ClockCircleOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  SyncOutlined,
  MoreOutlined,
  DownloadOutlined,
  LineChartOutlined
} from '@ant-design/icons';
import { TaskStatus, TaskType } from '../store/taskStore';

const { Text, Paragraph } = Typography;

// 任务项接口
export interface TaskItem {
  id: string;
  name: string;
  status: TaskStatus;
  type: TaskType;
  progress: number;
  startTime: Date;
  endTime?: Date;
  config: {
    id: string;
    name: string;
  };
  hasResults: boolean;
}

interface TaskListProps {
  /**
   * 任务列表
   */
  tasks: TaskItem[];
  /**
   * 加载状态
   */
  loading?: boolean;
  /**
   * 查看任务详情回调
   */
  onViewTask: (id: string) => void;
  /**
   * 删除任务回调
   */
  onDeleteTask: (id: string) => void;
  /**
   * 停止任务回调
   */
  onStopTask?: (id: string) => void;
  /**
   * 导出日志回调
   */
  onExportLogs?: (id: string) => void;
  /**
   * 查看结果回调
   */
  onViewResults?: (id: string) => void;
}

/**
 * 任务列表组件
 * 展示所有任务及其状态
 */
const TaskList = ({
  tasks,
  loading = false,
  onViewTask,
  onDeleteTask,
  onStopTask,
  onExportLogs,
  onViewResults
}: TaskListProps) => {
  const [searchText, setSearchText] = useState('');
  const [statusFilter, setStatusFilter] = useState<TaskStatus | 'all'>('all');
  const [typeFilter, setTypeFilter] = useState<TaskType | 'all'>('all');

  // 状态图标映射
  const statusIconMap = {
    'pending': <ClockCircleOutlined style={{ color: '#d9d9d9' }} />,
    'running': <SyncOutlined spin style={{ color: '#1890ff' }} />,
    'success': <CheckCircleOutlined style={{ color: '#52c41a' }} />,
    'failed': <CloseCircleOutlined style={{ color: '#f5222d' }} />
  };

  // 状态文本映射
  const statusTextMap = {
    'pending': '等待中',
    'running': '运行中',
    'success': '已完成',
    'failed': '失败'
  };

  // 类型标签颜色映射
  const typeColorMap = {
    'training': 'blue',
    'backtest': 'green',
    'data_init': 'orange'
  };

  // 类型显示文本映射
  const typeTextMap = {
    'training': '模型训练',
    'backtest': '策略回测',
    'data_init': '数据初始化'
  };

  // 过滤任务列表
  const filteredTasks = tasks.filter(task => {
    const matchesSearch = task.name.toLowerCase().includes(searchText.toLowerCase()) || 
                          task.config.name.toLowerCase().includes(searchText.toLowerCase());
    const matchesStatus = statusFilter === 'all' || task.status === statusFilter;
    const matchesType = typeFilter === 'all' || task.type === typeFilter;
    
    return matchesSearch && matchesStatus && matchesType;
  });

  // 计算任务运行时间
  const calculateDuration = (startTime: Date, endTime?: Date) => {
    const end = endTime || new Date();
    const durationMs = end.getTime() - startTime.getTime();
    
    // 小于1分钟
    if (durationMs < 60000) {
      return `${Math.floor(durationMs / 1000)}秒`;
    }
    // 小于1小时
    else if (durationMs < 3600000) {
      return `${Math.floor(durationMs / 60000)}分钟`;
    }
    // 大于1小时
    else {
      const hours = Math.floor(durationMs / 3600000);
      const minutes = Math.floor((durationMs % 3600000) / 60000);
      return `${hours}小时${minutes}分钟`;
    }
  };

  // 渲染任务菜单
  const renderTaskMenu = (task: TaskItem) => {
    return {
      items: [
        {
          key: 'view',
          label: '查看详情',
          icon: <EyeOutlined />,
          onClick: () => onViewTask(task.id)
        },
        ...(task.status === 'running' ? [
          {
            key: 'stop',
            label: '停止任务',
            icon: <CloseCircleOutlined />,
            danger: true,
            onClick: () => onStopTask && onStopTask(task.id)
          }
        ] : []),
        {
          key: 'export',
          label: '导出日志',
          icon: <DownloadOutlined />,
          onClick: () => onExportLogs && onExportLogs(task.id)
        },
        ...(task.hasResults ? [
          {
            key: 'results',
            label: '查看结果',
            icon: <LineChartOutlined />,
            onClick: () => onViewResults && onViewResults(task.id)
          }
        ] : []),
        {
          key: 'delete',
          label: '删除任务',
          icon: <DeleteOutlined />,
          danger: true,
          onClick: () => onDeleteTask(task.id)
        }
      ]
    };
  };

  // 渲染任务项
  const renderTaskItem = (task: TaskItem) => {
    return (
      <List.Item style={{ padding: 0, marginBottom: 16 }}>
        <Card
          hoverable
          size="small"
          style={{ width: '100%' }}
          onClick={() => onViewTask(task.id)}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
            <Space direction="vertical" style={{ width: '100%' }}>
              <div style={{ display: 'flex', alignItems: 'center' }}>
                <Badge 
                  status={
                    task.status === 'running' ? 'processing' :
                    task.status === 'success' ? 'success' :
                    task.status === 'failed' ? 'error' : 'default'
                  } 
                />
                <Text strong style={{ marginLeft: 8, marginRight: 8 }}>
                  {task.name}
                </Text>
                <Tag color={typeColorMap[task.type]}>
                  {typeTextMap[task.type]}
                </Tag>
                {task.hasResults && (
                  <Tag color="purple">有结果</Tag>
                )}
              </div>
              
              <div style={{ margin: '8px 0' }}>
                <Text type="secondary">
                  配置: {task.config.name}
                </Text>
              </div>
              
              {task.status === 'running' && (
                <Progress 
                  percent={task.progress} 
                  size="small" 
                  status="active" 
                  showInfo={false}
                  style={{ marginBottom: 8 }}
                />
              )}
              
              <div style={{ fontSize: '12px', color: '#999' }}>
                <Space size="small">
                  <span>开始: {task.startTime.toLocaleString()}</span>
                  {task.endTime && <span>结束: {task.endTime.toLocaleString()}</span>}
                  <span>耗时: {calculateDuration(task.startTime, task.endTime)}</span>
                </Space>
              </div>
            </Space>
            
            <Space>
              <Tooltip title="查看详情">
                <Button
                  type="text"
                  size="small"
                  icon={<EyeOutlined />}
                  onClick={(e) => {
                    e.stopPropagation();
                    onViewTask(task.id);
                  }}
                />
              </Tooltip>
              
              {task.hasResults && (
                <Tooltip title="查看结果">
                  <Button
                    type="text"
                    size="small"
                    icon={<LineChartOutlined />}
                    onClick={(e) => {
                      e.stopPropagation();
                      onViewResults && onViewResults(task.id);
                    }}
                  />
                </Tooltip>
              )}
              
              <Dropdown menu={renderTaskMenu(task)} trigger={['click']}>
                <Button
                  type="text"
                  size="small"
                  icon={<MoreOutlined />}
                  onClick={(e) => e.stopPropagation()}
                />
              </Dropdown>
            </Space>
          </div>
        </Card>
      </List.Item>
    );
  };

  return (
    <div className="task-list-container">
      <div style={{ marginBottom: 16 }}>
        <Input
          placeholder="搜索任务..."
          prefix={<SearchOutlined />}
          value={searchText}
          onChange={(e) => setSearchText(e.target.value)}
          allowClear
          style={{ marginBottom: 8 }}
        />
        
        <Space>
          <Dropdown
            menu={{
              items: [
                { key: 'all', label: '全部状态' },
                { key: 'pending', label: '等待中', icon: statusIconMap.pending },
                { key: 'running', label: '运行中', icon: statusIconMap.running },
                { key: 'success', label: '已完成', icon: statusIconMap.success },
                { key: 'failed', label: '失败', icon: statusIconMap.failed },
              ],
              onClick: ({ key }) => setStatusFilter(key as TaskStatus | 'all')
            }}
          >
            <Button icon={<FilterOutlined />}>
              状态: {statusFilter === 'all' ? '全部' : statusTextMap[statusFilter as TaskStatus]}
            </Button>
          </Dropdown>
          
          <Dropdown
            menu={{
              items: [
                { key: 'all', label: '全部类型' },
                { key: 'training', label: typeTextMap.training },
                { key: 'backtest', label: typeTextMap.backtest },
                { key: 'data_init', label: typeTextMap.data_init },
              ],
              onClick: ({ key }) => setTypeFilter(key as TaskType | 'all')
            }}
          >
            <Button icon={<FilterOutlined />}>
              类型: {typeFilter === 'all' ? '全部' : typeTextMap[typeFilter as TaskType]}
            </Button>
          </Dropdown>
        </Space>
      </div>
      
      {filteredTasks.length > 0 ? (
        <List
          dataSource={filteredTasks}
          renderItem={renderTaskItem}
          loading={loading}
        />
      ) : (
        <Empty
          image={Empty.PRESENTED_IMAGE_SIMPLE}
          description={
            searchText || statusFilter !== 'all' || typeFilter !== 'all' 
              ? '没有找到匹配的任务' 
              : '暂无任务'
          }
        />
      )}
    </div>
  );
};

export default TaskList;
