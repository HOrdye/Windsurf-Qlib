import * as React from 'react';
import { Card, Progress, Typography, Badge, Tag, Space, Timeline, Empty, Button } from 'antd';
import { 
  CheckCircleOutlined, 
  CloseCircleOutlined, 
  SyncOutlined, 
  ClockCircleOutlined,
  DownloadOutlined
} from '@ant-design/icons';
import { TaskStatus, TaskType } from '../store/taskStore';

const { Title, Text } = Typography;

interface TaskProgressProps {
  taskId: string;
  name: string;
  status: TaskStatus;
  progress: number;
  type: TaskType;
  startTime: Date;
  endTime?: Date;
  logs: string[];
  onLogExport?: () => void;
  onTaskStop?: () => void;
}

/**
 * 任务进度组件
 * 显示任务状态、进度条、日志等
 */
const TaskProgress: React.FC<TaskProgressProps> = ({
  taskId,
  name,
  status,
  progress,
  type,
  startTime,
  endTime,
  logs = [],
  onLogExport,
  onTaskStop
}) => {
  const [visibleLogs, setVisibleLogs] = React.useState<string[]>([]);
  const [showAllLogs, setShowAllLogs] = React.useState(false);
  const MAX_VISIBLE_LOGS = 10;

  // 状态图标映射
  const statusIconMap = {
    'pending': <ClockCircleOutlined style={{ color: '#d9d9d9' }} />,
    'running': <SyncOutlined spin style={{ color: '#1890ff' }} />,
    'success': <CheckCircleOutlined style={{ color: '#52c41a' }} />,
    'failed': <CloseCircleOutlined style={{ color: '#f5222d' }} />
  };

  // 状态显示文本映射
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

  // 更新可见日志
  React.useEffect(() => {
    if (showAllLogs) {
      setVisibleLogs(logs);
    } else {
      // 仅显示最新的N条日志
      setVisibleLogs(logs.slice(-MAX_VISIBLE_LOGS));
    }
  }, [logs, showAllLogs]);

  // 计算任务运行时间
  const calculateDuration = () => {
    const end = endTime || new Date();
    const durationMs = end.getTime() - startTime.getTime();
    
    const seconds = Math.floor(durationMs / 1000) % 60;
    const minutes = Math.floor(durationMs / (1000 * 60)) % 60;
    const hours = Math.floor(durationMs / (1000 * 60 * 60));
    
    return `${hours > 0 ? `${hours}小时 ` : ''}${minutes}分钟 ${seconds}秒`;
  };

  return (
    <Card>
      <Space direction="vertical" style={{ width: '100%' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
          <Space>
            <Badge status={
              status === 'running' ? 'processing' :
              status === 'success' ? 'success' :
              status === 'failed' ? 'error' : 'default'
            } />
            <Title level={4} style={{ margin: 0 }}>{name}</Title>
            <Tag color={typeColorMap[type]}>{typeTextMap[type]}</Tag>
          </Space>
          <Space>
            {status === 'running' && (
              <Button type="default" danger onClick={onTaskStop}>
                停止任务
              </Button>
            )}
            <Button 
              type="text" 
              icon={<DownloadOutlined />} 
              onClick={onLogExport}
            >
              导出日志
            </Button>
          </Space>
        </div>
        
        <Progress
          percent={progress}
          status={
            status === 'running' ? 'active' :
            status === 'success' ? 'success' :
            status === 'failed' ? 'exception' : 'normal'
          }
          strokeWidth={10}
        />
        
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
          <Space>
            <Text strong>状态:</Text>
            <Space>
              {statusIconMap[status]}
              <Text>{statusTextMap[status]}</Text>
            </Space>
          </Space>
          <Space>
            <Text strong>运行时间:</Text>
            <Text>{calculateDuration()}</Text>
          </Space>
        </div>
        
        <div style={{ marginBottom: 16 }}>
          <Text strong>开始时间: </Text>
          <Text>{startTime.toLocaleString()}</Text>
          {endTime && (
            <>
              <br />
              <Text strong>结束时间: </Text>
              <Text>{endTime.toLocaleString()}</Text>
            </>
          )}
        </div>
        
        <Title level={5}>任务日志</Title>
        <div style={{ 
          backgroundColor: '#f5f5f5', 
          padding: 16, 
          borderRadius: 4,
          maxHeight: '300px',
          overflow: 'auto',
          marginBottom: 16
        }}>
          {visibleLogs.length > 0 ? (
            <Timeline>
              {visibleLogs.map((log, index) => (
                <Timeline.Item key={index}>
                  <div style={{ fontFamily: 'monospace', whiteSpace: 'pre-wrap' }}>
                    {log}
                  </div>
                </Timeline.Item>
              ))}
            </Timeline>
          ) : (
            <Empty description="暂无日志" image={Empty.PRESENTED_IMAGE_SIMPLE} />
          )}
        </div>
        
        {logs.length > MAX_VISIBLE_LOGS && (
          <Button 
            type="link" 
            onClick={() => setShowAllLogs(!showAllLogs)}
          >
            {showAllLogs ? '显示最新日志' : `显示全部日志 (${logs.length}条)`}
          </Button>
        )}
      </Space>
    </Card>
  );
};

export default TaskProgress;
