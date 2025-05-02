import React, { useState } from 'react';
import { Card, Row, Col, Select, Button, Tabs, Upload, Space, Radio, Divider, Switch, Table } from 'antd';
import { 
  UploadOutlined, 
  DownloadOutlined, 
  FileExcelOutlined,
  SyncOutlined
} from '@ant-design/icons';
import ReactECharts from 'echarts-for-react';

const { TabPane } = Tabs;
const { Option } = Select;

// 模拟净值曲线数据
const mockNavData = {
  dates: Array.from({ length: 100 }).map((_, i) => {
    const date = new Date(2020, 0, 1);
    date.setDate(date.getDate() + i);
    return date.toISOString().split('T')[0];
  }),
  strategy: Array.from({ length: 100 }).map((_, i) => {
    let value = 1.0;
    for (let j = 0; j <= i; j++) {
      value *= (1 + (Math.random() * 0.02 - 0.01));
    }
    return parseFloat(value.toFixed(4));
  }),
  benchmark: Array.from({ length: 100 }).map((_, i) => {
    let value = 1.0;
    for (let j = 0; j <= i; j++) {
      value *= (1 + (Math.random() * 0.015 - 0.007));
    }
    return parseFloat(value.toFixed(4));
  })
};

// 模拟特征重要性数据
const mockFeatureImpData = [
  { value: 0.23, name: 'MACD' },
  { value: 0.19, name: 'RSI' },
  { value: 0.15, name: 'KDJ' },
  { value: 0.12, name: 'BOLL' },
  { value: 0.09, name: 'MA' },
  { value: 0.07, name: '成交量' },
  { value: 0.06, name: 'ROC' },
  { value: 0.05, name: 'ATR' },
  { value: 0.03, name: 'CCI' },
  { value: 0.01, name: 'OBV' }
];

// 模拟绩效指标数据
const mockPerformanceData = [
  { key: '1', metric: '年化收益率', strategy: '18.25%', benchmark: '8.37%' },
  { key: '2', metric: '夏普比率', strategy: '1.87', benchmark: '0.92' },
  { key: '3', metric: '最大回撤', strategy: '-15.28%', benchmark: '-21.43%' },
  { key: '4', metric: '波动率', strategy: '12.53%', benchmark: '15.89%' },
  { key: '5', metric: 'Alpha', strategy: '0.08', benchmark: '0.00' },
  { key: '6', metric: 'Beta', strategy: '0.75', benchmark: '1.00' },
  { key: '7', metric: '信息比率', strategy: '1.35', benchmark: '0.00' },
  { key: '8', metric: '胜率', strategy: '62.34%', benchmark: '51.82%' }
];

// 月度回报热力图数据生成函数
const generateHeatmapData = () => {
  const years = ['2020', '2021', '2022', '2023', '2024'];
  const months = ['1月', '2月', '3月', '4月', '5月', '6月', '7月', '8月', '9月', '10月', '11月', '12月'];
  const data = [];

  for (let y = 0; y < years.length; y++) {
    for (let m = 0; m < months.length; m++) {
      // 生成-10%到+10%之间的随机收益率
      const value = parseFloat((Math.random() * 20 - 10).toFixed(2));
      data.push([m, y, value]);
    }
  }

  return {
    years,
    months,
    data
  };
};

const heatmapData = generateHeatmapData();

// 修改组件类型定义，避免使用 React.FC
const Visualization = (): JSX.Element => {
  const [selectedResult, setSelectedResult] = useState<string>('result1');
  const [compareMode, setCompareMode] = useState<boolean>(false);
  const [comparedResult, setComparedResult] = useState<string | null>(null);
  const [chartType, setChartType] = useState<string>('nav');

  // 净值曲线图配置
  const getNavChartOption = () => {
    return {
      title: {
        text: '策略净值曲线',
        left: 'center'
      },
      tooltip: {
        trigger: 'axis',
        formatter: function(params: any) {
          const date = params[0].axisValue;
          let html = `${date}<br/>`;
          
          for (let i = 0; i < params.length; i++) {
            const param = params[i];
            html += `${param.marker}${param.seriesName}: ${param.value}<br/>`;
          }
          
          return html;
        }
      },
      legend: {
        data: ['策略', '基准'],
        bottom: '0%'
      },
      grid: {
        left: '3%',
        right: '4%',
        bottom: '10%',
        top: '15%',
        containLabel: true
      },
      xAxis: {
        type: 'category',
        boundaryGap: false,
        data: mockNavData.dates
      },
      yAxis: {
        type: 'value',
        axisLabel: {
          formatter: '{value}'
        }
      },
      series: [
        {
          name: '策略',
          type: 'line',
          data: mockNavData.strategy,
          symbol: 'none',
          lineStyle: {
            width: 2
          },
          itemStyle: {
            color: '#1890ff'
          }
        },
        {
          name: '基准',
          type: 'line',
          data: mockNavData.benchmark,
          symbol: 'none',
          lineStyle: {
            width: 2
          },
          itemStyle: {
            color: '#52c41a'
          }
        }
      ]
    };
  };

  // 特征重要性图表配置
  const getFeatureImpOption = () => {
    return {
      title: {
        text: '特征重要性 Top10',
        left: 'center'
      },
      tooltip: {
        trigger: 'item',
        formatter: '{b}: {c} ({d}%)'
      },
      series: [
        {
          name: '特征重要性',
          type: 'pie',
          radius: ['40%', '70%'],
          avoidLabelOverlap: false,
          itemStyle: {
            borderRadius: 10,
            borderColor: '#fff',
            borderWidth: 2
          },
          label: {
            show: true,
            formatter: '{b}: {d}%'
          },
          emphasis: {
            label: {
              show: true,
              fontSize: 16,
              fontWeight: 'bold'
            }
          },
          labelLine: {
            show: true
          },
          data: mockFeatureImpData.map(item => ({
            value: item.value,
            name: item.name
          }))
        }
      ]
    };
  };

  // 月度回报热力图配置
  const getHeatmapOption = () => {
    return {
      title: {
        top: 10,
        left: 'center',
        text: '月度回报热力图'
      },
      tooltip: {
        position: 'top',
        formatter: function (params: any) {
          const month = heatmapData.months[params.data[0]];
          const year = heatmapData.years[params.data[1]];
          const value = params.data[2];
          return `${year}年${month}: ${value}%`;
        }
      },
      grid: {
        left: '10%',
        right: '10%',
        top: '15%',
        bottom: '10%'
      },
      xAxis: {
        type: 'category',
        data: heatmapData.months,
        splitArea: {
          show: true
        }
      },
      yAxis: {
        type: 'category',
        data: heatmapData.years,
        splitArea: {
          show: true
        }
      },
      visualMap: {
        min: -10,
        max: 10,
        calculable: true,
        orient: 'horizontal',
        left: 'center',
        bottom: '0%',
        inRange: {
          color: ['#a50026', '#d73027', '#f46d43', '#fdae61', '#fee090', '#ffffbf', '#e0f3f8', '#abd9e9', '#74add1', '#4575b4', '#313695']
        }
      },
      series: [{
        name: '月度回报',
        type: 'heatmap',
        data: heatmapData.data,
        label: {
          show: false
        },
        emphasis: {
          itemStyle: {
            shadowBlur: 10,
            shadowColor: 'rgba(0, 0, 0, 0.5)'
          }
        }
      }]
    };
  };

  // 表格列配置
  const columns = [
    {
      title: '指标',
      dataIndex: 'metric',
      key: 'metric',
    },
    {
      title: '策略',
      dataIndex: 'strategy',
      key: 'strategy',
    },
    {
      title: '基准',
      dataIndex: 'benchmark',
      key: 'benchmark',
    },
  ];

  return (
    <div>
      <Card 
        title="数据可视化" 
        bordered={false}
        extra={
          <Space>
            <Button icon={<SyncOutlined />}>刷新</Button>
            <Upload>
              <Button icon={<UploadOutlined />}>导入结果</Button>
            </Upload>
            <Button icon={<DownloadOutlined />} type="primary">导出CSV</Button>
          </Space>
        }
      >
        <Row gutter={[16, 16]}>
          <Col span={24}>
            <Space>
              <Select
                style={{ width: 180 }}
                placeholder="选择回测结果"
                value={selectedResult}
                onChange={setSelectedResult}
              >
                <Option value="result1">CSI300 LGBM模型 (2025-04-02)</Option>
                <Option value="result2">CSI300 MLP模型 (2025-04-01)</Option>
                <Option value="result3">CSI500 Random Forest (2025-03-29)</Option>
              </Select>
              
              <Switch 
                checkedChildren="比较模式" 
                unCheckedChildren="单结果"
                checked={compareMode}
                onChange={setCompareMode}
              />
              
              {compareMode && (
                <Select
                  style={{ width: 180 }}
                  placeholder="选择比较结果"
                  value={comparedResult}
                  onChange={setComparedResult}
                >
                  <Option value="result2">CSI300 MLP模型 (2025-04-01)</Option>
                  <Option value="result3">CSI500 Random Forest (2025-03-29)</Option>
                  <Option value="result4">CSI300 LSTM模型 (2025-03-28)</Option>
                </Select>
              )}
              
              <Radio.Group 
                value={chartType}
                onChange={e => setChartType(e.target.value)}
                buttonStyle="solid"
              >
                <Radio.Button value="nav">净值曲线</Radio.Button>
                <Radio.Button value="feature">特征重要性</Radio.Button>
                <Radio.Button value="heatmap">月度回报</Radio.Button>
              </Radio.Group>
            </Space>
          </Col>
          
          <Col span={24}>
            <Tabs defaultActiveKey="charts">
              <TabPane tab="图表" key="charts">
                <Row gutter={[16, 16]}>
                  <Col span={24}>
                    <div className="chart-container">
                      {chartType === 'nav' && (
                        <ReactECharts 
                          option={getNavChartOption()} 
                          style={{ height: 400 }} 
                        />
                      )}
                      {chartType === 'feature' && (
                        <ReactECharts 
                          option={getFeatureImpOption()} 
                          style={{ height: 400 }} 
                        />
                      )}
                      {chartType === 'heatmap' && (
                        <ReactECharts 
                          option={getHeatmapOption()} 
                          style={{ height: 400 }} 
                        />
                      )}
                    </div>
                  </Col>
                </Row>
              </TabPane>
              <TabPane tab="绩效指标" key="metrics">
                <Table 
                  dataSource={mockPerformanceData} 
                  columns={columns} 
                  pagination={false}
                  bordered
                  size="middle"
                />
              </TabPane>
              <TabPane tab="原始数据" key="data">
                <div style={{ maxHeight: '400px', overflow: 'auto' }}>
                  <pre>{JSON.stringify({
                    dates: mockNavData.dates.slice(0, 10),
                    strategy: mockNavData.strategy.slice(0, 10),
                    benchmark: mockNavData.benchmark.slice(0, 10),
                    // ... 更多数据
                  }, null, 2)}</pre>
                  <Divider />
                  <Button icon={<FileExcelOutlined />}>导出完整数据</Button>
                </div>
              </TabPane>
            </Tabs>
          </Col>
        </Row>
      </Card>
    </div>
  );
};

export default Visualization;
