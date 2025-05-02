import React, { useState, useEffect, useRef } from 'react';
import { Card, Tabs, Select, Empty, Spin, Button, Row, Col, Typography, Divider, Space, Radio, Tooltip, Statistic } from 'antd';
import { 
  LineChartOutlined, 
  BarChartOutlined, 
  PieChartOutlined, 
  TableOutlined,
  DownloadOutlined,
  ReloadOutlined,
  InfoCircleOutlined
} from '@ant-design/icons';
import { useTaskStore } from '../store/taskStore';
import { Task } from '../store/taskStore';
import { saveAs } from 'file-saver';

// 导入图表库
// 注意：实际使用时需要安装这些依赖
// npm install --save echarts echarts-for-react
import ReactECharts from 'echarts-for-react';
import * as echarts from 'echarts';

const { TabPane } = Tabs;
const { Title, Text, Paragraph } = Typography;
const { Option } = Select;

interface DataVisualizationProps {
  taskId?: string;
  height?: number | string;
  showTitle?: boolean;
}

const DataVisualization: React.FC<DataVisualizationProps> = ({ 
  taskId,
  height = 600,
  showTitle = true
}) => {
  const { tasks, getTaskById } = useTaskStore();
  const [selectedTaskId, setSelectedTaskId] = useState<string | undefined>(taskId);
  const [selectedTask, setSelectedTask] = useState<Task | undefined>(undefined);
  const [loading, setLoading] = useState<boolean>(false);
  const [chartType, setChartType] = useState<string>('line');
  
  // 图表引用
  const lineChartRef = useRef<any>(null);
  const barChartRef = useRef<any>(null);
  const pieChartRef = useRef<any>(null);
  
  // 当props中的taskId变化时更新选中的任务
  useEffect(() => {
    if (taskId) {
      setSelectedTaskId(taskId);
    }
  }, [taskId]);
  
  // 当选中的任务ID变化时，更新选中的任务对象
  useEffect(() => {
    if (selectedTaskId) {
      const task = getTaskById(selectedTaskId);
      setSelectedTask(task);
    } else {
      setSelectedTask(undefined);
    }
  }, [selectedTaskId, tasks, getTaskById]);
  
  // 处理任务选择变化
  const handleTaskChange = (value: string) => {
    setSelectedTaskId(value);
  };
  
  // 处理图表类型变化
  const handleChartTypeChange = (e: any) => {
    setChartType(e.target.value);
  };
  
  // 导出数据为CSV
  const exportCSV = () => {
    if (!selectedTask || !selectedTask.metrics) return;
    
    try {
      // 将指标数据转换为CSV格式
      const metrics = selectedTask.metrics;
      let csvContent = 'data:text/csv;charset=utf-8,';
      
      // 添加表头
      const headers = Object.keys(metrics);
      csvContent += headers.join(',') + '\n';
      
      // 添加数据行
      // 这里假设所有指标都是数值或可以转换为字符串的
      const values = headers.map(header => metrics[header]);
      csvContent += values.join(',') + '\n';
      
      // 创建下载链接
      const encodedUri = encodeURI(csvContent);
      const link = document.createElement('a');
      link.setAttribute('href', encodedUri);
      link.setAttribute('download', `task-${selectedTask.id.substring(0, 8)}-metrics.csv`);
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    } catch (error) {
      console.error('导出CSV失败:', error);
    }
  };
  
  // 导出图表为图片
  const exportChart = (chartRef: any) => {
    if (!chartRef.current || !selectedTask) return;
    
    try {
      const base64 = chartRef.current.getEchartsInstance().getDataURL();
      const link = document.createElement('a');
      link.href = base64;
      link.download = `task-${selectedTask.id.substring(0, 8)}-chart.png`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    } catch (error) {
      console.error('导出图表失败:', error);
    }
  };
  
  // 渲染指标卡片
  const renderMetricCards = () => {
    if (!selectedTask || !selectedTask.metrics) {
      return (
        <Empty description="无可用指标数据" />
      );
    }
    
    const metrics = selectedTask.metrics;
    
    return (
      <Row gutter={[16, 16]}>
        {Object.entries(metrics).map(([key, value]) => {
          // 跳过非数值类型的指标或复杂对象
          if (typeof value === 'object' || Array.isArray(value)) {
            return null;
          }
          
          return (
            <Col span={8} key={key}>
              <Card>
                <CustomStatistic
                  title={key}
                  value={typeof value === 'number' ? value : String(value)}
                  precision={typeof value === 'number' ? 4 : 0}
                  valueStyle={{ color: '#3f8600' }}
                />
              </Card>
            </Col>
          );
        })}
      </Row>
    );
  };
  
  // 渲染折线图
  const renderLineChart = () => {
    if (!selectedTask || !selectedTask.metrics) {
      return (
        <Empty description="无可用指标数据" />
      );
    }
    
    // 这里假设metrics中有一个returns字段，包含了收益率数据
    // 实际应用中需要根据实际数据结构调整
    const returns = selectedTask.metrics.returns || [];
    
    if (!Array.isArray(returns) || returns.length === 0) {
      return (
        <Empty description="无可用收益率数据" />
      );
    }
    
    const option = {
      title: {
        text: '策略收益率',
        left: 'center'
      },
      tooltip: {
        trigger: 'axis',
        formatter: '{a} <br/>{b}: {c}%'
      },
      xAxis: {
        type: 'category',
        data: returns.map((_, index) => `Day ${index + 1}`)
      },
      yAxis: {
        type: 'value',
        axisLabel: {
          formatter: '{value}%'
        }
      },
      series: [
        {
          name: '收益率',
          type: 'line',
          data: returns,
          markPoint: {
            data: [
              { type: 'max', name: '最大值' },
              { type: 'min', name: '最小值' }
            ]
          }
        }
      ]
    };
    
    return (
      <div>
        <ReactECharts 
          option={option} 
          style={{ height: 400 }}
          ref={lineChartRef}
        />
        <div style={{ textAlign: 'right', marginTop: 16 }}>
          <Button 
            icon={<DownloadOutlined />}
            onClick={() => exportChart(lineChartRef)}
          >
            导出图表
          </Button>
        </div>
      </div>
    );
  };
  
  // 渲染柱状图
  const renderBarChart = () => {
    if (!selectedTask || !selectedTask.metrics) {
      return (
        <Empty description="无可用指标数据" />
      );
    }
    
    // 这里假设metrics中有一个performance字段，包含了各项性能指标
    // 实际应用中需要根据实际数据结构调整
    const performance = selectedTask.metrics.performance || {};
    
    if (typeof performance !== 'object' || Object.keys(performance).length === 0) {
      return (
        <Empty description="无可用性能指标数据" />
      );
    }
    
    const option = {
      title: {
        text: '模型性能指标',
        left: 'center'
      },
      tooltip: {
        trigger: 'axis',
        axisPointer: {
          type: 'shadow'
        }
      },
      grid: {
        left: '3%',
        right: '4%',
        bottom: '3%',
        containLabel: true
      },
      xAxis: {
        type: 'category',
        data: Object.keys(performance)
      },
      yAxis: {
        type: 'value'
      },
      series: [
        {
          name: '性能指标',
          type: 'bar',
          data: Object.values(performance)
        }
      ]
    };
    
    return (
      <div>
        <ReactECharts 
          option={option} 
          style={{ height: 400 }}
          ref={barChartRef}
        />
        <div style={{ textAlign: 'right', marginTop: 16 }}>
          <Button 
            icon={<DownloadOutlined />}
            onClick={() => exportChart(barChartRef)}
          >
            导出图表
          </Button>
        </div>
      </div>
    );
  };
  
  // 渲染饼图
  const renderPieChart = () => {
    if (!selectedTask || !selectedTask.metrics) {
      return (
        <Empty description="无可用指标数据" />
      );
    }
    
    // 这里假设metrics中有一个allocation字段，包含了资产配置数据
    // 实际应用中需要根据实际数据结构调整
    const allocation = selectedTask.metrics.allocation || {};
    
    if (typeof allocation !== 'object' || Object.keys(allocation).length === 0) {
      return (
        <Empty description="无可用资产配置数据" />
      );
    }
    
    const option = {
      title: {
        text: '资产配置',
        left: 'center'
      },
      tooltip: {
        trigger: 'item',
        formatter: '{a} <br/>{b}: {c} ({d}%)'
      },
      legend: {
        orient: 'vertical',
        left: 'left',
        data: Object.keys(allocation)
      },
      series: [
        {
          name: '资产配置',
          type: 'pie',
          radius: '50%',
          data: Object.entries(allocation).map(([name, value]) => ({
            name,
            value
          })),
          emphasis: {
            itemStyle: {
              shadowBlur: 10,
              shadowOffsetX: 0,
              shadowColor: 'rgba(0, 0, 0, 0.5)'
            }
          }
        }
      ]
    };
    
    return (
      <div>
        <ReactECharts 
          option={option} 
          style={{ height: 400 }}
          ref={pieChartRef}
        />
        <div style={{ textAlign: 'right', marginTop: 16 }}>
          <Button 
            icon={<DownloadOutlined />}
            onClick={() => exportChart(pieChartRef)}
          >
            导出图表
          </Button>
        </div>
      </div>
    );
  };
  
  // 渲染指标表格
  const renderMetricsTable = () => {
    if (!selectedTask || !selectedTask.metrics) {
      return (
        <Empty description="无可用指标数据" />
      );
    }
    
    const metrics = selectedTask.metrics;
    
    return (
      <div>
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr style={{ backgroundColor: '#f5f5f5' }}>
              <th style={{ padding: '12px', textAlign: 'left', borderBottom: '1px solid #e8e8e8' }}>指标</th>
              <th style={{ padding: '12px', textAlign: 'right', borderBottom: '1px solid #e8e8e8' }}>值</th>
            </tr>
          </thead>
          <tbody>
            {Object.entries(metrics).map(([key, value]) => {
              // 跳过复杂对象和数组
              if (typeof value === 'object' && value !== null && !Array.isArray(value)) {
                return null;
              }
              
              // 如果是数组，显示数组长度
              const displayValue = Array.isArray(value) 
                ? `[Array(${value.length})]` 
                : String(value);
              
              return (
                <tr key={key} style={{ borderBottom: '1px solid #e8e8e8' }}>
                  <td style={{ padding: '12px', textAlign: 'left' }}>{key}</td>
                  <td style={{ padding: '12px', textAlign: 'right', fontFamily: 'monospace' }}>{displayValue}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
        <div style={{ textAlign: 'right', marginTop: 16 }}>
          <Button 
            icon={<DownloadOutlined />}
            onClick={exportCSV}
          >
            导出CSV
          </Button>
        </div>
      </div>
    );
  };
  
  // 渲染可视化内容
  const renderVisualization = () => {
    if (!selectedTask) {
      return (
        <Empty description="请选择一个任务查看数据可视化" />
      );
    }
    
    if (selectedTask.status !== 'success') {
      return (
        <Empty description="只有成功完成的任务才能查看数据可视化" />
      );
    }
    
    if (!selectedTask.metrics) {
      return (
        <Empty description="该任务没有可视化数据" />
      );
    }
    
    // 根据选择的图表类型渲染不同的图表
    switch (chartType) {
      case 'line':
        return renderLineChart();
      case 'bar':
        return renderBarChart();
      case 'pie':
        return renderPieChart();
      case 'table':
        return renderMetricsTable();
      default:
        return renderLineChart();
    }
  };
  
  // 获取可用的已完成任务
  const completedTasks = tasks.filter(task => task.status === 'success' && task.metrics);
  
  return (
    <Spin spinning={loading}>
      <Card
        title={showTitle ? "数据可视化" : null}
        style={{ height }}
        bodyStyle={{ height: showTitle ? 'calc(100% - 57px)' : '100%', padding: 16 }}
        extra={
          <Space>
            <Select
              placeholder="选择任务"
              style={{ width: 200 }}
              value={selectedTaskId}
              onChange={handleTaskChange}
            >
              {completedTasks.map(task => (
                <Option key={task.id} value={task.id}>
                  {task.name}
                </Option>
              ))}
            </Select>
            <Radio.Group 
              value={chartType} 
              onChange={handleChartTypeChange}
              buttonStyle="solid"
            >
              <Tooltip title="折线图">
                <Radio.Button value="line"><LineChartOutlined /></Radio.Button>
              </Tooltip>
              <Tooltip title="柱状图">
                <Radio.Button value="bar"><BarChartOutlined /></Radio.Button>
              </Tooltip>
              <Tooltip title="饼图">
                <Radio.Button value="pie"><PieChartOutlined /></Radio.Button>
              </Tooltip>
              <Tooltip title="表格">
                <Radio.Button value="table"><TableOutlined /></Radio.Button>
              </Tooltip>
            </Radio.Group>
          </Space>
        }
      >
        <div style={{ height: '100%', overflowY: 'auto' }}>
          {selectedTask && (
            <div style={{ marginBottom: 16 }}>
              <Title level={4}>{selectedTask.name}</Title>
              <Paragraph type="secondary">
                任务ID: {selectedTask.id}
              </Paragraph>
              <Divider style={{ margin: '12px 0' }} />
            </div>
          )}
          
          {renderVisualization()}
        </div>
      </Card>
    </Spin>
  );
};

interface StatisticProps {
  title: string;
  value: string | number;
  precision?: number;
  valueStyle?: any;
}

const CustomStatistic = ({ title, value, precision = 0, valueStyle = {} }: StatisticProps) => {
  const formattedValue = typeof value === 'number' 
    ? value.toFixed(precision) 
    : value;
  
  return (
    <div>
      <div style={{ color: 'rgba(0, 0, 0, 0.45)', fontSize: '14px', marginBottom: '4px' }}>
        {title}
      </div>
      <div style={{ color: valueStyle.color || 'rgba(0, 0, 0, 0.85)', fontSize: '24px', fontWeight: 'bold' }}>
        {formattedValue}
      </div>
    </div>
  );
};

export default DataVisualization;
