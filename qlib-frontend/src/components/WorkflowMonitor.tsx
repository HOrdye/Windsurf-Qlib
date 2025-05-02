import React, { useState, useEffect } from 'react';
import { Card, Steps, Typography, Tag, Space, Button, Collapse, Empty, List, Progress, Tooltip, Divider, Modal, message, Statistic, Row, Col, Tabs } from 'antd';
import { 
  CheckCircleOutlined, 
  CloseCircleOutlined, 
  LoadingOutlined,
  PlayCircleOutlined,
  PauseCircleOutlined,
  SyncOutlined,
  ClockCircleOutlined,
  BarChartOutlined,
  DeleteOutlined,
  LineChartOutlined,
  PieChartOutlined,
  AreaChartOutlined
} from '@ant-design/icons';
import { useWorkflowStore } from '../store/workflowStore';
import { useTaskStore } from '../store/taskStore';
import { Workflow, WorkflowStatus, WorkflowStep } from '../services/workflowManager';
import WorkflowManager from '../services/workflowManager';
// 移除recharts导入，使用Ant Design图表组件
import { Line, Column, Pie } from '@ant-design/plots';

const { Title, Text, Paragraph } = Typography;
const { Step } = Steps;
const { Panel } = Collapse;

// 工作流类型名称映射
const workflowTypeNames = {
  full: '完整工作流',
  train_backtest: '训练和回测',
  backtest_only: '仅回测'
};

// 工作流状态名称映射
const workflowStatusNames = {
  pending: '等待中',
  running: '运行中',
  completed: '已完成',
  failed: '失败',
  canceled: '已取消'
};

// 工作流状态颜色映射
const workflowStatusColors = {
  pending: 'default',
  running: 'processing',
  completed: 'success',
  failed: 'error',
  canceled: 'warning'
};

// 步骤类型名称映射
const stepTypeNames = {
  data_init: '数据初始化',
  training: '模型训练',
  backtest: '策略回测'
};

interface WorkflowMonitorProps {
  height?: number | string;
  showTitle?: boolean;
  workflowId?: string;
  onWorkflowSelect?: (workflowId: string) => void;
}

const WorkflowMonitor: React.FC<WorkflowMonitorProps> = ({ 
  height = 600,
  showTitle = true,
  workflowId,
  onWorkflowSelect
}) => {
  const { 
    workflows, 
    selectedWorkflowId: storeSelectedWorkflowId,
    selectWorkflow,
    deleteWorkflow
  } = useWorkflowStore();
  
  const { tasks, getTaskById } = useTaskStore();
  const [loading, setLoading] = useState<boolean>(false);
  const [resultModalVisible, setResultModalVisible] = useState<boolean>(false);
  const [resultData, setResultData] = useState<any>(null);
  
  // 使用props中的workflowId或store中的selectedWorkflowId
  const currentWorkflowId = workflowId || storeSelectedWorkflowId;
  const selectedWorkflow = currentWorkflowId ? 
    workflows.find(workflow => workflow.id === currentWorkflowId) : 
    null;
  
  const workflowManager = WorkflowManager.getInstance();
  
  // 处理工作流选择
  const handleWorkflowSelect = (id: string) => {
    selectWorkflow(id);
    if (onWorkflowSelect) {
      onWorkflowSelect(id);
    }
  };
  
  // 处理工作流取消
  const handleCancelWorkflow = async (id: string) => {
    setLoading(true);
    try {
      await workflowManager.cancelWorkflow(id);
    } catch (error) {
      console.error('取消工作流失败:', error);
    } finally {
      setLoading(false);
    }
  };
  
  // 处理工作流删除
  const handleDeleteWorkflow = (id: string) => {
    deleteWorkflow(id);
  };
  
  // 处理查看结果
  const handleViewResults = async (workflowId: string) => {
    setLoading(true);
    try {
      // 模拟从服务器获取结果数据
      // 实际实现中，这里应该调用API获取工作流结果
      console.log('获取工作流结果:', workflowId);
      
      // 模拟数据
      const mockResults = {
        workflowId,
        metrics: {
          accuracy: 0.85,
          precision: 0.83,
          recall: 0.87,
          f1Score: 0.85,
          sharpeRatio: 1.23,
          maxDrawdown: -0.15,
          annualReturn: 0.21
        },
        charts: {
          returns: [
            { date: '2025-01-01', strategy: 0.015, benchmark: 0.010 },
            { date: '2025-01-02', strategy: 0.025, benchmark: 0.015 },
            { date: '2025-01-03', strategy: 0.020, benchmark: 0.012 },
            { date: '2025-01-04', strategy: 0.035, benchmark: 0.020 },
            { date: '2025-01-05', strategy: 0.045, benchmark: 0.025 },
            { date: '2025-01-06', strategy: 0.040, benchmark: 0.022 },
            { date: '2025-01-07', strategy: 0.055, benchmark: 0.030 },
            { date: '2025-01-08', strategy: 0.065, benchmark: 0.035 },
            { date: '2025-01-09', strategy: 0.075, benchmark: 0.040 },
            { date: '2025-01-10', strategy: 0.085, benchmark: 0.045 },
            { date: '2025-01-11', strategy: 0.095, benchmark: 0.050 },
            { date: '2025-01-12', strategy: 0.105, benchmark: 0.055 },
            { date: '2025-01-13', strategy: 0.115, benchmark: 0.060 },
            { date: '2025-01-14', strategy: 0.125, benchmark: 0.065 },
            { date: '2025-01-15', strategy: 0.135, benchmark: 0.070 }
          ],
          dailyReturns: [
            { date: '2025-01-01', return: 0.015 },
            { date: '2025-01-02', return: 0.010 },
            { date: '2025-01-03', return: -0.005 },
            { date: '2025-01-04', return: 0.015 },
            { date: '2025-01-05', return: 0.010 },
            { date: '2025-01-06', return: -0.005 },
            { date: '2025-01-07', return: 0.015 },
            { date: '2025-01-08', return: 0.010 },
            { date: '2025-01-09', return: 0.010 },
            { date: '2025-01-10', return: 0.010 },
            { date: '2025-01-11', return: 0.010 },
            { date: '2025-01-12', return: 0.010 },
            { date: '2025-01-13', return: 0.010 },
            { date: '2025-01-14', return: 0.010 },
            { date: '2025-01-15', return: 0.010 }
          ],
          assetAllocation: [
            { name: '股票', value: 45 },
            { name: '债券', value: 30 },
            { name: '现金', value: 15 },
            { name: '商品', value: 10 }
          ],
          riskMetrics: [
            { name: '波动率', value: 0.12 },
            { name: '最大回撤', value: 0.15 },
            { name: '夏普比率', value: 1.23 },
            { name: '信息比率', value: 0.85 },
            { name: '贝塔系数', value: 0.75 }
          ]
        },
        timestamp: new Date().toISOString()
      };
      
      setResultData(mockResults);
      setResultModalVisible(true);
    } catch (error) {
      console.error('获取工作流结果失败:', error);
      message.error('获取结果失败，请稍后重试');
    } finally {
      setLoading(false);
    }
  };
  
  // 计算工作流总进度
  const calculateWorkflowProgress = (workflow: Workflow): number => {
    if (!workflow.steps.length) return 0;
    
    let totalProgress = 0;
    let completedSteps = 0;
    
    for (const step of workflow.steps) {
      if (step.status === 'success') {
        totalProgress += 100;
        completedSteps++;
      } else if (step.status === 'running' && step.taskId) {
        const task = getTaskById(step.taskId);
        if (task) {
          totalProgress += task.progress;
        }
        completedSteps++;
      } else if (step.status === 'failed') {
        completedSteps++;
      }
    }
    
    return Math.round(totalProgress / workflow.steps.length);
  };
  
  // 获取步骤状态
  const getStepStatus = (step: WorkflowStep): 'wait' | 'process' | 'finish' | 'error' => {
    switch (step.status) {
      case 'pending':
        return 'wait';
      case 'running':
        return 'process';
      case 'success':
        return 'finish';
      case 'failed':
        return 'error';
      default:
        return 'wait';
    }
  };
  
  // 渲染工作流列表项
  const renderWorkflowItem = (workflow: Workflow) => {
    const isSelected = workflow.id === currentWorkflowId;
    const isRunning = workflow.status === WorkflowStatus.RUNNING;
    const isPending = workflow.status === WorkflowStatus.PENDING;
    const isCompleted = workflow.status === WorkflowStatus.COMPLETED;
    const isFailed = workflow.status === WorkflowStatus.FAILED;
    const isCanceled = workflow.status === WorkflowStatus.CANCELED;
    
    const progress = calculateWorkflowProgress(workflow);
    
    return (
      <List.Item 
        key={workflow.id}
        className={isSelected ? 'selected-workflow-item' : ''}
        style={{ 
          cursor: 'pointer',
          padding: '12px',
          borderLeft: isSelected ? '3px solid #1890ff' : '3px solid transparent',
          backgroundColor: isSelected ? '#f0f8ff' : 'transparent'
        }}
        onClick={() => handleWorkflowSelect(workflow.id)}
        actions={[
          <Space>
            {(isRunning || isPending) && (
              <Tooltip title="取消工作流">
                <Button 
                  type="text" 
                  icon={<CloseCircleOutlined />} 
                  size="small"
                  onClick={(e) => {
                    e.stopPropagation();
                    handleCancelWorkflow(workflow.id);
                  }}
                  loading={loading}
                />
              </Tooltip>
            )}
            {(isCompleted || isFailed || isCanceled) && (
              <Tooltip title="删除工作流">
                <Button 
                  type="text" 
                  danger
                  icon={<DeleteOutlined />} 
                  size="small"
                  onClick={(e) => {
                    e.stopPropagation();
                    handleDeleteWorkflow(workflow.id);
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
                    handleViewResults(workflow.id);
                  }}
                  loading={loading}
                />
              </Tooltip>
            )}
          </Space>
        ]}
      >
        <List.Item.Meta
          title={
            <Space>
              <Text strong>{workflow.name}</Text>
              <Tag color="blue">{workflowTypeNames[workflow.type]}</Tag>
              <Tag color={workflowStatusColors[workflow.status]}>
                {workflowStatusNames[workflow.status]}
              </Tag>
            </Space>
          }
          description={
            <div>
              <div style={{ marginBottom: 8 }}>
                <Text type="secondary">
                  开始时间: {workflow.startTime.toLocaleString()}
                  {workflow.endTime && ` | 结束时间: ${workflow.endTime.toLocaleString()}`}
                </Text>
              </div>
              <Progress 
                percent={progress} 
                status={
                  workflow.status === WorkflowStatus.FAILED ? 'exception' : 
                  workflow.status === WorkflowStatus.CANCELED ? 'exception' :
                  workflow.status === WorkflowStatus.COMPLETED ? 'success' : 'active'
                }
                size="small"
              />
            </div>
          }
        />
      </List.Item>
    );
  };
  
  // 渲染工作流详情
  const renderWorkflowDetails = () => {
    if (!selectedWorkflow) {
      return (
        <Empty 
          description="选择一个工作流查看详情" 
          image={Empty.PRESENTED_IMAGE_SIMPLE}
        />
      );
    }
    
    return (
      <div style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
        <div style={{ marginBottom: 16 }}>
          <Title level={4}>{selectedWorkflow.name}</Title>
          <Space>
            <Tag color="blue">{workflowTypeNames[selectedWorkflow.type]}</Tag>
            <Tag color={workflowStatusColors[selectedWorkflow.status]}>
              {workflowStatusNames[selectedWorkflow.status]}
            </Tag>
          </Space>
          <Paragraph type="secondary">
            <div>开始时间: {selectedWorkflow.startTime.toLocaleString()}</div>
            {selectedWorkflow.endTime && <div>结束时间: {selectedWorkflow.endTime.toLocaleString()}</div>}
          </Paragraph>
        </div>
        
        <Divider style={{ margin: '8px 0' }} />
        
        <div style={{ marginBottom: 16 }}>
          <Text strong>工作流进度</Text>
          <Progress 
            percent={calculateWorkflowProgress(selectedWorkflow)} 
            status={
              selectedWorkflow.status === WorkflowStatus.FAILED ? 'exception' : 
              selectedWorkflow.status === WorkflowStatus.CANCELED ? 'exception' :
              selectedWorkflow.status === WorkflowStatus.COMPLETED ? 'success' : 'active'
            }
          />
        </div>
        
        <div style={{ marginBottom: 16 }}>
          <Text strong>步骤</Text>
          <Steps 
            direction="vertical" 
            current={selectedWorkflow.steps.findIndex(step => step.status === 'running')}
            style={{ marginTop: 16 }}
          >
            {selectedWorkflow.steps.map((step, index) => {
              const task = step.taskId ? getTaskById(step.taskId) : undefined;
              
              return (
                <Step
                  key={step.id}
                  title={step.name}
                  description={
                    <div>
                      <div>{stepTypeNames[step.type]}</div>
                      {task && (
                        <div style={{ marginTop: 8 }}>
                          <Progress 
                            percent={Math.round(task.progress)} 
                            size="small"
                            status={
                              step.status === 'failed' ? 'exception' : 
                              step.status === 'success' ? 'success' : 'active'
                            }
                          />
                        </div>
                      )}
                    </div>
                  }
                  status={getStepStatus(step)}
                  icon={
                    step.status === 'running' ? <LoadingOutlined /> :
                    step.status === 'success' ? <CheckCircleOutlined /> :
                    step.status === 'failed' ? <CloseCircleOutlined /> :
                    <ClockCircleOutlined />
                  }
                />
              );
            })}
          </Steps>
        </div>
        
        <Collapse defaultActiveKey={['tasks']} style={{ marginTop: 16 }}>
          <Panel header="关联任务" key="tasks">
            <List
              dataSource={selectedWorkflow.steps.filter(step => step.taskId)}
              renderItem={(step) => {
                const task = step.taskId ? getTaskById(step.taskId) : undefined;
                
                if (!task) return null;
                
                return (
                  <List.Item>
                    <List.Item.Meta
                      title={
                        <Space>
                          <Text>{task.name}</Text>
                          <Tag color={
                            task.status === 'running' ? 'processing' :
                            task.status === 'success' ? 'success' :
                            task.status === 'failed' ? 'error' : 'default'
                          }>
                            {
                              task.status === 'running' ? '运行中' :
                              task.status === 'success' ? '已完成' :
                              task.status === 'failed' ? '失败' : '等待中'
                            }
                          </Tag>
                        </Space>
                      }
                      description={
                        <Progress 
                          percent={Math.round(task.progress)} 
                          size="small"
                          status={
                            task.status === 'failed' ? 'exception' : 
                            task.status === 'success' ? 'success' : 'active'
                          }
                        />
                      }
                    />
                  </List.Item>
                );
              }}
            />
          </Panel>
        </Collapse>
        
        <div style={{ marginTop: 'auto', textAlign: 'right' }}>
          <Space>
            {(selectedWorkflow.status === WorkflowStatus.RUNNING || selectedWorkflow.status === WorkflowStatus.PENDING) && (
              <Button 
                type="primary" 
                danger
                icon={<CloseCircleOutlined />}
                onClick={() => handleCancelWorkflow(selectedWorkflow.id)}
                loading={loading}
              >
                取消工作流
              </Button>
            )}
            {selectedWorkflow.status === WorkflowStatus.COMPLETED && (
              <Button 
                type="primary"
                icon={<BarChartOutlined />}
                onClick={() => handleViewResults(selectedWorkflow.id)}
                loading={loading}
              >
                查看结果
              </Button>
            )}
          </Space>
        </div>
      </div>
    );
  };
  
  // 渲染结果图表
  const renderResultCharts = (resultData: any) => {
    // 准备折线图数据格式
    const prepareLineData = () => {
      const data: any[] = [];
      if (resultData?.charts?.returns) {
        resultData.charts.returns.forEach((item: any) => {
          data.push({ date: item.date, value: item.strategy, type: '策略收益' });
          data.push({ date: item.date, value: item.benchmark, type: '基准收益' });
        });
      }
      return data;
    };

    // 准备柱状图数据格式
    const prepareDailyReturnData = () => {
      return resultData?.charts?.dailyReturns?.map((item: any) => ({
        date: item.date,
        return: item.return,
        color: item.return >= 0 ? '#82ca9d' : '#ff6b6b'
      })) || [];
    };

    return (
      <Tabs defaultActiveKey="1">
        {[
          {
            key: '1',
            label: (
              <span>
                <LineChartOutlined />
                累计收益
              </span>
            ),
            children: (
              <Card title="策略与基准累计收益对比" bordered={false}>
                <Line 
                  height={300}
                  data={prepareLineData()} 
                  xField="date" 
                  yField="value" 
                  seriesField="type" 
                  color={['#8884d8', '#82ca9d']}
                  tooltip={{
                    formatter: (datum) => {
                      return { name: datum.type, value: `${(Number(datum.value) * 100).toFixed(2)}%` };
                    }
                  }}
                />
              </Card>
            ),
          },
          {
            key: '2',
            label: (
              <span>
                <BarChartOutlined />
                日收益率
              </span>
            ),
            children: (
              <Card title="策略每日收益" bordered={false}>
                <Column 
                  height={300}
                  data={prepareDailyReturnData()} 
                  xField="date" 
                  yField="return" 
                  colorField="color"
                  tooltip={{
                    formatter: (datum) => {
                      return { name: '日收益率', value: `${(Number(datum.return) * 100).toFixed(2)}%` };
                    }
                  }}
                />
              </Card>
            ),
          },
          {
            key: '3',
            label: (
              <span>
                <PieChartOutlined />
                资产配置
              </span>
            ),
            children: (
              <Card title="策略资产配置" bordered={false}>
                <Pie 
                  height={300}
                  data={resultData?.charts?.assetAllocation || []} 
                  angleField="value" 
                  colorField="name" 
                  color={['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#8884d8', '#82ca9d']}
                  radius={0.8}
                  label={{
                    type: 'outer',
                    content: '{name}: {percentage}',
                  }}
                  tooltip={{
                    formatter: (datum) => {
                      return { name: datum.name, value: `${datum.value}%` };
                    }
                  }}
                />
              </Card>
            ),
          },
          {
            key: '4',
            label: (
              <span>
                <AreaChartOutlined />
                风险指标
              </span>
            ),
            children: (
              <Card title="策略风险指标" bordered={false}>
                <Column 
                  height={300}
                  data={resultData?.charts?.riskMetrics || []} 
                  xField="name" 
                  yField="value" 
                  color={['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#8884d8', '#82ca9d']}
                />
              </Card>
            ),
          },
        ]}
      </Tabs>
    );
  };
  
  // 渲染结果模态框
  const renderResultModal = () => {
    if (!resultData) return null;
    
    return (
      <Modal
        title="工作流执行结果"
        open={resultModalVisible}
        onCancel={() => setResultModalVisible(false)}
        width={900}
        style={{ top: 20 }}
        footer={[
          <Button key="close" onClick={() => setResultModalVisible(false)}>
            关闭
          </Button>,
          <Button 
            key="download" 
            type="primary" 
            onClick={() => message.success('结果下载功能即将实现')}
          >
            下载结果
          </Button>
        ]}
      >
        <div style={{ maxHeight: '80vh', overflowY: 'auto', padding: '0 10px' }}>
          <Divider orientation="left">性能指标</Divider>
          <Row gutter={[16, 16]}>
            {Object.entries(resultData.metrics).map(([key, value]) => (
              <Col key={key} xs={24} sm={12} md={8} lg={6}>
                <Card size="small">
                  <Statistic
                    title={key.replace(/([A-Z])/g, ' $1').replace(/^./, str => str.toUpperCase())}
                    value={value as number}
                    precision={2}
                    valueStyle={{ 
                      color: key.includes('Drawdown') ? '#cf1322' : 
                             (key.includes('Ratio') || key.includes('Return') || key.includes('accuracy')) ? '#3f8600' : '#1890ff' 
                    }}
                  />
                </Card>
              </Col>
            ))}
          </Row>
          
          <Divider orientation="left">量化分析图表</Divider>
          {renderResultCharts(resultData)}
        </div>
      </Modal>
    );
  };
  
  // 按状态分组工作流
  const activeWorkflows = workflows.filter(w => 
    w.status === WorkflowStatus.RUNNING || w.status === WorkflowStatus.PENDING
  );
  
  const completedWorkflows = workflows.filter(w => 
    w.status === WorkflowStatus.COMPLETED || 
    w.status === WorkflowStatus.FAILED || 
    w.status === WorkflowStatus.CANCELED
  );
  
  return (
    <Card
      title={showTitle ? "工作流监控" : null}
      style={{ height }}
      bodyStyle={{ height: showTitle ? 'calc(100% - 57px)' : '100%', padding: 0 }}
    >
      {renderResultModal()}
      <div style={{ display: 'flex', height: '100%' }}>
        <div style={{ width: '30%', borderRight: '1px solid #f0f0f0', height: '100%', overflowY: 'auto' }}>
          <div style={{ padding: '12px 16px', borderBottom: '1px solid #f0f0f0' }}>
            <Text strong>活动工作流 ({activeWorkflows.length})</Text>
          </div>
          <List
            dataSource={activeWorkflows}
            renderItem={renderWorkflowItem}
            locale={{ emptyText: <Empty description="暂无活动工作流" image={Empty.PRESENTED_IMAGE_SIMPLE} /> }}
          />
          
          <div style={{ padding: '12px 16px', borderBottom: '1px solid #f0f0f0', borderTop: '1px solid #f0f0f0' }}>
            <Text strong>已完成工作流 ({completedWorkflows.length})</Text>
          </div>
          <List
            dataSource={completedWorkflows}
            renderItem={renderWorkflowItem}
            locale={{ emptyText: <Empty description="暂无已完成工作流" image={Empty.PRESENTED_IMAGE_SIMPLE} /> }}
          />
        </div>
        
        <div style={{ width: '70%', padding: 16, height: '100%', overflowY: 'auto' }}>
          {renderWorkflowDetails()}
        </div>
      </div>
    </Card>
  );
};

export default WorkflowMonitor;
