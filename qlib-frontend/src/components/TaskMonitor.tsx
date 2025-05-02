import React, { useState, useEffect, useRef } from 'react';
import { Card, Row, Col, List, Typography, Progress, Tag, Button, Tabs, Empty, Spin, Tooltip, Divider, Space } from 'antd';
import { 
  PlayCircleOutlined, 
  PauseCircleOutlined,
  CloseCircleOutlined,
  CheckCircleOutlined,
  SyncOutlined,
  DownloadOutlined,
  EyeOutlined,
  DeleteOutlined,
  FileTextOutlined,
  BarChartOutlined
} from '@ant-design/icons';
import { useTaskStore } from '../store/taskStore';
import { Task, TaskStatus, TaskType } from '../store/taskStore';
import TaskManager from '../services/taskManager';
import WebSocketService, { MessageType } from '../services/websocket';
import { saveAs } from 'file-saver';

const { Title, Text, Paragraph } = Typography;
const { TabPane } = Tabs;

// 任务类型标签颜色映射
const taskTypeColors = {
  training: 'blue',
  backtest: 'green',
  data_init: 'purple'
};

// 任务状态标签颜色映射
const taskStatusColors = {
  pending: 'default',
  running: 'processing',
  success: 'success',
  failed: 'error'
};

// 任务类型名称映射
const taskTypeNames = {
  training: '模型训练',
  backtest: '策略回测',
  data_init: '数据初始化'
};

// 任务状态名称映射
const taskStatusNames = {
  pending: '等待中',
  running: '运行中',
  success: '已完成',
  failed: '失败'
};

interface TaskMonitorProps {
  showTitle?: boolean;
  height?: number | string;
  onTaskSelect?: (taskId: string) => void;
  selectedTaskId?: string;
}

const TaskMonitor: React.FC<TaskMonitorProps> = ({ 
  showTitle = true, 
  height = 600,
  onTaskSelect,
  selectedTaskId
}) => {
  const { 
    tasks, 
    selectedTaskId: storeSelectedTaskId, 
    selectTask,
    getSelectedTask,
    deleteTask
  } = useTaskStore();
  
  const [activeTab, setActiveTab] = useState<string>('running');
  const [loading, setLoading] = useState<boolean>(false);
  const logEndRef = useRef<HTMLDivElement>(null);
  const taskManager = TaskManager.getInstance();
  const ws = WebSocketService.getInstance();
  
  // 使用props中的selectedTaskId或store中的selectedTaskId
  const currentSelectedTaskId = selectedTaskId || storeSelectedTaskId;
  const selectedTask = currentSelectedTaskId ? 
    tasks.find(task => task.id === currentSelectedTaskId) : 
    null;
  
  // 根据状态过滤任务
  const runningTasks = tasks.filter(task => task.status === 'pending' || task.status === 'running');
  const completedTasks = tasks.filter(task => task.status === 'success' || task.status === 'failed');
  
  // 滚动到日志底部
  useEffect(() => {
    if (logEndRef.current) {
      logEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [selectedTask?.log]);
  
  // 注册WebSocket消息处理器
  useEffect(() => {
    // 确保WebSocket连接
    if (!ws.isConnected()) {
      ws.connect();
    }
    
    // 注册任务进度更新处理器
    const unsubscribeProgress = ws.on(MessageType.TASK_PROGRESS, (payload) => {
      if (payload && payload.taskId) {
        const { taskId, progress } = payload;
        const taskStore = useTaskStore.getState();
        taskStore.updateTaskProgress(taskId, progress);
      }
    });
    
    // 注册任务日志更新处理器
    const unsubscribeLog = ws.on(MessageType.TASK_LOG, (payload) => {
      if (payload && payload.taskId) {
        const { taskId, message } = payload;
        const taskStore = useTaskStore.getState();
        taskStore.addTaskLog(taskId, message);
      }
    });
    
    return () => {
      unsubscribeProgress();
      unsubscribeLog();
    };
  }, []);
  
  // 处理任务选择
  const handleTaskSelect = (taskId: string) => {
    selectTask(taskId);
    if (onTaskSelect) {
      onTaskSelect(taskId);
    }
  };
  
  // 处理任务取消
  const handleCancelTask = async (taskId: string) => {
    setLoading(true);
    try {
      await taskManager.cancelTask(taskId);
    } catch (error) {
      console.error('取消任务失败:', error);
    } finally {
      setLoading(false);
    }
  };
  
  // 处理任务删除
  const handleDeleteTask = (taskId: string) => {
    deleteTask(taskId);
  };
  
  // 导出任务日志
  const handleExportLog = (task: Task) => {
    const logContent = task.log.join('\n');
    const blob = new Blob([logContent], { type: 'text/plain;charset=utf-8' });
    saveAs(blob, `task-log-${task.id.substring(0, 8)}.txt`);
  };
  
  // 渲染任务列表项
  const renderTaskItem = (task: Task) => {
    const isSelected = task.id === currentSelectedTaskId;
    const isRunning = task.status === 'running';
    const isPending = task.status === 'pending';
    const isCompleted = task.status === 'success';
    const isFailed = task.status === 'failed';
    
    return (
      <List.Item 
        key={task.id}
        className={isSelected ? 'selected-task-item' : ''}
        style={{ 
          cursor: 'pointer',
          padding: '12px',
          borderLeft: isSelected ? '3px solid #1890ff' : '3px solid transparent',
          backgroundColor: isSelected ? '#f0f8ff' : 'transparent'
        }}
        onClick={() => handleTaskSelect(task.id)}
        actions={[
          <Space>
            {(isRunning || isPending) && (
              <Tooltip title="取消任务">
                <Button 
                  type="text" 
                  icon={<CloseCircleOutlined />} 
                  size="small"
                  onClick={(e) => {
                    e.stopPropagation();
                    handleCancelTask(task.id);
                  }}
                  loading={loading}
                />
              </Tooltip>
            )}
            {(isCompleted || isFailed) && (
              <Tooltip title="删除任务">
                <Button 
                  type="text" 
                  danger
                  icon={<DeleteOutlined />} 
                  size="small"
                  onClick={(e) => {
                    e.stopPropagation();
                    handleDeleteTask(task.id);
                  }}
                />
              </Tooltip>
            )}
            {(isCompleted || isFailed) && (
              <Tooltip title="导出日志">
                <Button 
                  type="text" 
                  icon={<DownloadOutlined />} 
                  size="small"
                  onClick={(e) => {
                    e.stopPropagation();
                    handleExportLog(task);
                  }}
                />
              </Tooltip>
            )}
            {isCompleted && (
              <Tooltip title="查看结果">
                <Button 
                  type="text" 
                  icon={<BarChartOutlined />} 
                  size="small"
                  onClick={(e) => {
                    e.stopPropagation();
                    // 查看结果的处理逻辑
                  }}
                />
              </Tooltip>
            )}
          </Space>
        ]}
      >
        <List.Item.Meta
          title={
            <Space>
              <Text strong>{task.name}</Text>
              <Tag color={taskTypeColors[task.type as TaskType]}>{taskTypeNames[task.type as TaskType]}</Tag>
              <Tag color={taskStatusColors[task.status as TaskStatus]}>{taskStatusNames[task.status as TaskStatus]}</Tag>
            </Space>
          }
          description={
            <div>
              <div style={{ marginBottom: 8 }}>
                <Text type="secondary">
                  开始时间: {task.startTime.toLocaleString()}
                  {task.endTime && ` | 结束时间: ${task.endTime.toLocaleString()}`}
                </Text>
              </div>
              <Progress 
                percent={Math.round(task.progress)} 
                status={
                  task.status === 'failed' ? 'exception' : 
                  task.status === 'success' ? 'success' : 'active'
                }
                size="small"
              />
            </div>
          }
        />
      </List.Item>
    );
  };
  
  // 渲染任务详情
  const renderTaskDetails = () => {
    if (!selectedTask) {
      return (
        <Empty 
          description="选择一个任务查看详情" 
          image={Empty.PRESENTED_IMAGE_SIMPLE}
        />
      );
    }
    
    return (
      <div style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
        <div style={{ marginBottom: 16 }}>
          <Title level={4}>{selectedTask.name}</Title>
          <Space>
            <Tag color={taskTypeColors[selectedTask.type as TaskType]}>
              {taskTypeNames[selectedTask.type as TaskType]}
            </Tag>
            <Tag color={taskStatusColors[selectedTask.status as TaskStatus]}>
              {taskStatusNames[selectedTask.status as TaskStatus]}
            </Tag>
          </Space>
          <Paragraph type="secondary">
            <div>开始时间: {selectedTask.startTime.toLocaleString()}</div>
            {selectedTask.endTime && <div>结束时间: {selectedTask.endTime.toLocaleString()}</div>}
          </Paragraph>
        </div>
        
        <Divider style={{ margin: '8px 0' }} />
        
        <div style={{ marginBottom: 16 }}>
          <Text strong>进度</Text>
          <Progress 
            percent={Math.round(selectedTask.progress)} 
            status={
              selectedTask.status === 'failed' ? 'exception' : 
              selectedTask.status === 'success' ? 'success' : 'active'
            }
          />
        </div>
        
        <Tabs defaultActiveKey="log">
          <TabPane tab="任务日志" key="log">
            <div 
              style={{ 
                height: 300, 
                overflowY: 'auto', 
                backgroundColor: '#f5f5f5',
                padding: 12,
                borderRadius: 4,
                fontFamily: 'monospace',
                fontSize: 12
              }}
            >
              {selectedTask.log.length === 0 ? (
                <Empty description="暂无日志" image={Empty.PRESENTED_IMAGE_SIMPLE} />
              ) : (
                selectedTask.log.map((log, index) => (
                  <div key={index}>{log}</div>
                ))
              )}
              <div ref={logEndRef} />
            </div>
          </TabPane>
          {selectedTask.metrics && (
            <TabPane tab="任务结果" key="result">
              <div style={{ height: 300, overflowY: 'auto' }}>
                {Object.entries(selectedTask.metrics).map(([key, value]) => (
                  <div key={key} style={{ marginBottom: 8 }}>
                    <Text strong>{key}: </Text>
                    <Text>{JSON.stringify(value)}</Text>
                  </div>
                ))}
              </div>
            </TabPane>
          )}
        </Tabs>
        
        <div style={{ marginTop: 'auto', textAlign: 'right' }}>
          <Space>
            {(selectedTask.status === 'running' || selectedTask.status === 'pending') && (
              <Button 
                type="primary" 
                danger
                icon={<CloseCircleOutlined />}
                onClick={() => handleCancelTask(selectedTask.id)}
                loading={loading}
              >
                取消任务
              </Button>
            )}
            {(selectedTask.status === 'success' || selectedTask.status === 'failed') && (
              <Button 
                icon={<DownloadOutlined />}
                onClick={() => handleExportLog(selectedTask)}
              >
                导出日志
              </Button>
            )}
            {selectedTask.status === 'success' && selectedTask.metrics && (
              <Button 
                type="primary"
                icon={<BarChartOutlined />}
                onClick={() => {/* 查看结果的处理逻辑 */}}
              >
                查看结果
              </Button>
            )}
          </Space>
        </div>
      </div>
    );
  };
  
  return (
    <Spin spinning={loading}>
      <Card
        title={showTitle ? "任务监控" : null}
        style={{ height }}
        bodyStyle={{ height: showTitle ? 'calc(100% - 57px)' : '100%', padding: 0 }}
      >
        <Row style={{ height: '100%' }}>
          <Col span={8} style={{ height: '100%', borderRight: '1px solid #f0f0f0' }}>
            <Tabs 
              activeKey={activeTab} 
              onChange={setActiveTab}
              style={{ padding: '0 16px' }}
            >
              <TabPane 
                tab={
                  <span>
                    <SyncOutlined spin={runningTasks.length > 0} />
                    进行中 ({runningTasks.length})
                  </span>
                } 
                key="running"
              >
                <List
                  dataSource={runningTasks}
                  renderItem={renderTaskItem}
                  style={{ 
                    height: showTitle ? 'calc(100vh - 220px)' : 'calc(100vh - 180px)',
                    overflowY: 'auto'
                  }}
                  locale={{ emptyText: <Empty description="暂无进行中的任务" /> }}
                />
              </TabPane>
              <TabPane 
                tab={
                  <span>
                    <FileTextOutlined />
                    已完成 ({completedTasks.length})
                  </span>
                } 
                key="completed"
              >
                <List
                  dataSource={completedTasks}
                  renderItem={renderTaskItem}
                  style={{ 
                    height: showTitle ? 'calc(100vh - 220px)' : 'calc(100vh - 180px)',
                    overflowY: 'auto'
                  }}
                  locale={{ emptyText: <Empty description="暂无已完成的任务" /> }}
                />
              </TabPane>
            </Tabs>
          </Col>
          <Col span={16} style={{ height: '100%', padding: 16 }}>
            {renderTaskDetails()}
          </Col>
        </Row>
      </Card>
    </Spin>
  );
};

export default TaskMonitor;
