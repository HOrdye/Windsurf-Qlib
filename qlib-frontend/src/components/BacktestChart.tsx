import React, { useState, useEffect } from 'react';
import ReactECharts from 'echarts-for-react';
import { Card, Radio, Button, Tooltip, Select, Space, Typography } from 'antd';
import { DownloadOutlined, QuestionCircleOutlined } from '@ant-design/icons';
import { RadioChangeEvent } from 'antd/lib/radio';

const { Title, Text } = Typography;
const { Option } = Select;

// 图表类型枚举
type ChartType = 'navCurve' | 'returns' | 'heatmap' | 'featureImportance' | 'prediction';

// 图表标题映射
const chartTitleMap: Record<ChartType, string> = {
  navCurve: '净值曲线',
  returns: '收益率分布',
  heatmap: '最大回撤热力图',
  featureImportance: '特征重要性',
  prediction: '预测对比'
};

interface BacktestChartProps {
  /**
   * 回测数据
   */
  data: any;
  /**
   * 图表标题
   */
  title?: string;
  /**
   * 可选择的图表类型
   */
  availableCharts?: ChartType[];
  /**
   * 导出数据回调
   */
  onExport?: () => void;
  /**
   * 图表高度
   */
  height?: number | string;
}

/**
 * 回测图表组件
 * 支持多种图表类型切换，如净值曲线、回撤热力图等
 */
const BacktestChart = ({
  data,
  title = '回测结果',
  availableCharts = ['navCurve', 'returns', 'heatmap', 'featureImportance'],
  onExport,
  height = 400
}: BacktestChartProps): JSX.Element => {
  const [chartType, setChartType] = useState<ChartType>(availableCharts[0]);
  const [compareMode, setCompareMode] = useState<boolean>(false);
  const [comparedStrategy, setComparedStrategy] = useState<string | null>(null);
  const [option, setOption] = useState<any>({});

  // 策略选项
  const strategies = [
    { label: 'LGBM模型', value: 'lgbm' },
    { label: 'MLP模型', value: 'mlp' },
    { label: 'LSTM模型', value: 'lstm' },
    { label: 'RF模型', value: 'rf' }
  ];

  // 图表类型改变
  const handleChartTypeChange = (e: RadioChangeEvent) => {
    setChartType(e.target.value as ChartType);
  };

  // 根据当前选择的图表类型生成ECharts配置
  useEffect(() => {
    let chartOption: any = {};

    switch (chartType) {
      case 'navCurve':
        chartOption = getNavCurveOption();
        break;
      case 'returns':
        chartOption = getReturnsDistributionOption();
        break;
      case 'heatmap':
        chartOption = getHeatmapOption();
        break;
      case 'featureImportance':
        chartOption = getFeatureImportanceOption();
        break;
      case 'prediction':
        chartOption = getPredictionComparisonOption();
        break;
      default:
        chartOption = {};
    }

    setOption(chartOption);
  }, [chartType, compareMode, comparedStrategy, data]);

  // 生成净值曲线图表选项
  const getNavCurveOption = () => {
    // 模拟数据 - 实际项目中应该使用传入的data参数
    const dates = Array.from({ length: 100 }).map((_, i) => {
      const date = new Date(2020, 0, 1);
      date.setDate(date.getDate() + i);
      return date.toISOString().split('T')[0];
    });

    const strategyNav = Array.from({ length: 100 }).map((_, i) => {
      let value = 1.0;
      for (let j = 0; j <= i; j++) {
        value *= (1 + (Math.random() * 0.02 - 0.01));
      }
      return parseFloat(value.toFixed(4));
    });

    const benchmarkNav = Array.from({ length: 100 }).map((_, i) => {
      let value = 1.0;
      for (let j = 0; j <= i; j++) {
        value *= (1 + (Math.random() * 0.015 - 0.007));
      }
      return parseFloat(value.toFixed(4));
    });

    return {
      title: {
        text: '策略净值曲线',
        left: 'center'
      },
      tooltip: {
        trigger: 'axis',
        axisPointer: {
          type: 'cross',
          label: {
            backgroundColor: '#6a7985'
          }
        }
      },
      legend: {
        data: compareMode ? ['策略', '基准', comparedStrategy] : ['策略', '基准'],
        bottom: 10
      },
      grid: {
        left: '3%',
        right: '4%',
        bottom: '15%',
        top: '15%',
        containLabel: true
      },
      xAxis: {
        type: 'category',
        boundaryGap: false,
        data: dates,
        axisLabel: {
          formatter: (value: string) => {
            return value.substring(5); // 仅显示月-日
          }
        }
      },
      yAxis: {
        type: 'value',
        axisLabel: {
          formatter: '{value}'
        },
        min: (value: any) => Math.floor(value.min * 0.9 * 10) / 10,
        max: (value: any) => Math.ceil(value.max * 1.1 * 10) / 10
      },
      series: [
        {
          name: '策略',
          type: 'line',
          data: strategyNav,
          symbol: 'none',
          smooth: true,
          lineStyle: {
            width: 2
          },
          itemStyle: {
            color: '#1890ff'
          },
          markPoint: {
            data: [
              { type: 'max', name: '最大值' },
              { type: 'min', name: '最小值' }
            ]
          }
        },
        {
          name: '基准',
          type: 'line',
          data: benchmarkNav,
          symbol: 'none',
          smooth: true,
          lineStyle: {
            width: 2
          },
          itemStyle: {
            color: '#52c41a'
          }
        },
        ...(compareMode && comparedStrategy ? [{
          name: comparedStrategy,
          type: 'line',
          data: Array.from({ length: 100 }).map((_, i) => {
            let value = 1.0;
            for (let j = 0; j <= i; j++) {
              value *= (1 + (Math.random() * 0.018 - 0.008));
            }
            return parseFloat(value.toFixed(4));
          }),
          symbol: 'none',
          smooth: true,
          lineStyle: {
            width: 2
          },
          itemStyle: {
            color: '#722ed1'
          }
        }] : [])
      ]
    };
  };

  // 生成收益率分布图表选项
  const getReturnsDistributionOption = () => {
    // 模拟数据
    const returns = Array.from({ length: 100 }).map(() => (Math.random() * 0.2 - 0.1));
    
    // 计算分布
    const bins = 20;
    const min = Math.min(...returns);
    const max = Math.max(...returns);
    const step = (max - min) / bins;
    
    const distribution = Array(bins).fill(0);
    returns.forEach(ret => {
      const index = Math.min(Math.floor((ret - min) / step), bins - 1);
      distribution[index]++;
    });
    
    const labels = Array(bins).fill(0).map((_, i) => {
      const start = (min + i * step).toFixed(2);
      const end = (min + (i + 1) * step).toFixed(2);
      return `${start}~${end}`;
    });

    return {
      title: {
        text: '收益率分布',
        left: 'center'
      },
      tooltip: {
        trigger: 'axis',
        axisPointer: {
          type: 'shadow'
        },
        formatter: '{b}: {c}'
      },
      grid: {
        left: '3%',
        right: '4%',
        bottom: '15%',
        top: '15%',
        containLabel: true
      },
      xAxis: {
        type: 'category',
        data: labels,
        axisLabel: {
          rotate: 45,
          interval: 1
        }
      },
      yAxis: {
        type: 'value',
        name: '频率'
      },
      series: [
        {
          name: '收益率',
          type: 'bar',
          data: distribution,
          itemStyle: {
            color: function(params: any) {
              // 根据收益率正负设置不同颜色
              const label = labels[params.dataIndex];
              const value = parseFloat(label.split('~')[0]);
              return value < 0 ? '#f5222d' : '#52c41a';
            }
          }
        }
      ]
    };
  };

  // 生成最大回撤热力图选项
  const getHeatmapOption = () => {
    // 生成模拟数据
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
      title: {
        top: 10,
        left: 'center',
        text: '月度回报热力图'
      },
      tooltip: {
        position: 'top',
        formatter: function (params: any) {
          const month = months[params.data[0]];
          const year = years[params.data[1]];
          const value = params.data[2];
          return `${year}年${month}: ${value}%`;
        }
      },
      grid: {
        left: '10%',
        right: '10%',
        top: '15%',
        bottom: '20%'
      },
      xAxis: {
        type: 'category',
        data: months,
        splitArea: {
          show: true
        }
      },
      yAxis: {
        type: 'category',
        data: years,
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
        data: data,
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

  // 生成特征重要性图表选项
  const getFeatureImportanceOption = () => {
    // 模拟数据
    const featureImpData = [
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
          data: featureImpData
        }
      ]
    };
  };

  // 生成预测值与实际值对比图表选项
  const getPredictionComparisonOption = () => {
    // 模拟数据
    const dates = Array.from({ length: 30 }).map((_, i) => {
      const date = new Date(2024, 3, 1);
      date.setDate(date.getDate() + i);
      return date.toISOString().split('T')[0];
    });
    
    const actual = Array.from({ length: 30 }).map(() => parseFloat((Math.random() * 20 + 90).toFixed(2)));
    
    const predicted = actual.map(value => {
      // 添加一些随机噪声，使预测值与实际值有所不同
      return parseFloat((value * (1 + (Math.random() * 0.1 - 0.05))).toFixed(2));
    });

    return {
      title: {
        text: '预测值与实际值对比',
        left: 'center'
      },
      tooltip: {
        trigger: 'axis',
        axisPointer: {
          type: 'cross'
        }
      },
      legend: {
        data: ['实际值', '预测值'],
        bottom: 10
      },
      grid: {
        left: '3%',
        right: '4%',
        bottom: '15%',
        top: '15%',
        containLabel: true
      },
      xAxis: {
        type: 'category',
        boundaryGap: false,
        data: dates,
        axisLabel: {
          formatter: (value: string) => {
            return value.substring(5); // 仅显示月-日
          }
        }
      },
      yAxis: {
        type: 'value',
        axisLabel: {
          formatter: '{value}'
        },
        min: (value: any) => Math.floor(value.min * 0.95),
        max: (value: any) => Math.ceil(value.max * 1.05)
      },
      series: [
        {
          name: '实际值',
          type: 'line',
          data: actual,
          symbol: 'circle',
          symbolSize: 6,
          itemStyle: {
            color: '#1890ff'
          }
        },
        {
          name: '预测值',
          type: 'line',
          data: predicted,
          symbol: 'triangle',
          symbolSize: 6,
          itemStyle: {
            color: '#fa8c16'
          }
        }
      ]
    };
  };

  return (
    <Card title={title} extra={
      <Space>
        <Tooltip title="下载数据为CSV">
          <Button 
            type="text" 
            icon={<DownloadOutlined />} 
            onClick={onExport}
          />
        </Tooltip>
        <Tooltip title="配置说明">
          <Button 
            type="text" 
            icon={<QuestionCircleOutlined />} 
          />
        </Tooltip>
      </Space>
    }>
      <Space direction="vertical" style={{ width: '100%' }}>
        <div style={{ marginBottom: 16 }}>
          <Space>
            <Radio.Group 
              value={chartType} 
              onChange={handleChartTypeChange}
              optionType="button"
              buttonStyle="solid"
            >
              {availableCharts.map(type => (
                <Radio.Button key={type} value={type}>
                  {chartTitleMap[type]}
                </Radio.Button>
              ))}
            </Radio.Group>
            
            {chartType === 'navCurve' && (
              <>
                <Text type="secondary">|</Text>
                <Space>
                  <Text>比较模式:</Text>
                  <Radio.Group
                    value={compareMode ? 'on' : 'off'}
                    onChange={(e) => setCompareMode(e.target.value === 'on')}
                    optionType="button"
                    buttonStyle="outline"
                    size="small"
                  >
                    <Radio.Button value="off">关闭</Radio.Button>
                    <Radio.Button value="on">开启</Radio.Button>
                  </Radio.Group>
                  
                  {compareMode && (
                    <Select 
                      placeholder="选择对比策略"
                      style={{ width: 120 }}
                      value={comparedStrategy}
                      onChange={setComparedStrategy}
                    >
                      {strategies.map(strategy => (
                        <Option key={strategy.value} value={strategy.value}>
                          {strategy.label}
                        </Option>
                      ))}
                    </Select>
                  )}
                </Space>
              </>
            )}
          </Space>
        </div>
        
        <ReactECharts 
          option={option} 
          style={{ height, width: '100%' }} 
          notMerge={true}
          lazyUpdate={true}
        />
      </Space>
    </Card>
  );
};

export default BacktestChart;
