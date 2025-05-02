import React from 'react';
import ReactECharts from 'echarts-for-react';
import { Card, Row, Col, Radio, Table } from 'antd';
import { RadioChangeEvent } from 'antd/lib/radio';
import type { Position } from '../../types/backtest';

// 扩展 Position 接口，添加组件中使用的属性
interface ExtendedPosition extends Position {
  volume: number;
  cost: number;
  pnl: number;
  pnlRatio: number;
}

interface PositionAnalysisProps {
  positions: ExtendedPosition[];
  loading?: boolean;
}

// 修改组件类型定义，避免使用 React.FC
const PositionAnalysis = ({
  positions,
  loading = false
}: PositionAnalysisProps): JSX.Element => {
  const [chartType, setChartType] = React.useState<'pie' | 'treemap'>('pie');

  // 计算持仓分布数据
  const getPositionDistribution = () => {
    const total = positions.reduce((sum, pos) => sum + pos.marketValue, 0);
    return positions.map(pos => ({
      name: pos.symbol,
      value: pos.marketValue,
      percentage: (pos.marketValue / total * 100).toFixed(2),
      pnlRatio: (pos.pnlRatio * 100).toFixed(2)
    }));
  };

  // 生成饼图配置
  const getPieOption = () => {
    const data = getPositionDistribution();
    return {
      title: {
        text: '持仓分布',
        left: 'center'
      },
      tooltip: {
        trigger: 'item',
        formatter: (params: any) => {
          const { name, value, data } = params;
          return `${name}<br/>市值: ${value.toFixed(2)}<br/>占比: ${data.percentage}%<br/>收益率: ${data.pnlRatio}%`;
        }
      },
      legend: {
        orient: 'vertical',
        right: 10,
        top: 'center',
        type: 'scroll'
      },
      series: [
        {
          name: '持仓分布',
          type: 'pie',
          radius: ['40%', '70%'],
          avoidLabelOverlap: true,
          itemStyle: {
            borderRadius: 10,
            borderColor: '#fff',
            borderWidth: 2
          },
          label: {
            show: false,
            position: 'center'
          },
          emphasis: {
            label: {
              show: true,
              fontSize: '20',
              fontWeight: 'bold'
            }
          },
          labelLine: {
            show: false
          },
          data
        }
      ]
    };
  };

  // 生成矩形树图配置
  const getTreemapOption = () => {
    const data = getPositionDistribution();
    return {
      title: {
        text: '持仓分布',
        left: 'center'
      },
      tooltip: {
        formatter: (params: any) => {
          const { name, value, data } = params;
          return `${name}<br/>市值: ${value.toFixed(2)}<br/>占比: ${data.percentage}%<br/>收益率: ${data.pnlRatio}%`;
        }
      },
      series: [
        {
          type: 'treemap',
          data: data.map(item => ({
            ...item,
            itemStyle: {
              color: parseFloat(item.pnlRatio) >= 0 ? '#91cc75' : '#ee6666'
            }
          })),
          label: {
            show: true,
            formatter: '{b}: {c}'
          }
        }
      ]
    };
  };

  // 表格列定义
  const columns = [
    {
      title: '股票代码',
      dataIndex: 'symbol',
      key: 'symbol',
    },
    {
      title: '持仓数量',
      dataIndex: 'volume',
      key: 'volume',
      sorter: (a: ExtendedPosition, b: ExtendedPosition) => a.volume - b.volume,
    },
    {
      title: '成本',
      dataIndex: 'cost',
      key: 'cost',
      render: (value: number) => value.toFixed(2),
      sorter: (a: ExtendedPosition, b: ExtendedPosition) => a.cost - b.cost,
    },
    {
      title: '市值',
      dataIndex: 'marketValue',
      key: 'marketValue',
      render: (value: number) => value.toFixed(2),
      sorter: (a: ExtendedPosition, b: ExtendedPosition) => a.marketValue - b.marketValue,
    },
    {
      title: '盈亏',
      dataIndex: 'pnl',
      key: 'pnl',
      render: (value: number) => (
        <span style={{ color: value >= 0 ? '#3f8600' : '#cf1322' }}>
          {value.toFixed(2)}
        </span>
      ),
      sorter: (a: ExtendedPosition, b: ExtendedPosition) => a.pnl - b.pnl,
    },
    {
      title: '收益率',
      dataIndex: 'pnlRatio',
      key: 'pnlRatio',
      render: (value: number) => (
        <span style={{ color: value >= 0 ? '#3f8600' : '#cf1322' }}>
          {(value * 100).toFixed(2)}%
        </span>
      ),
      sorter: (a: ExtendedPosition, b: ExtendedPosition) => a.pnlRatio - b.pnlRatio,
    },
  ];

  return (
    <div className="position-analysis">
      <Row gutter={[16, 16]}>
        <Col span={24}>
          <Card
            title="持仓分析"
            extra={
              <Radio.Group
                value={chartType}
                onChange={(e: RadioChangeEvent) => setChartType(e.target.value)}
              >
                <Radio.Button value="pie">饼图</Radio.Button>
                <Radio.Button value="treemap">矩形树图</Radio.Button>
              </Radio.Group>
            }
          >
            <ReactECharts
              option={chartType === 'pie' ? getPieOption() : getTreemapOption()}
              style={{ height: '400px' }}
              loading={loading}
            />
          </Card>
        </Col>
      </Row>
      <Row gutter={[16, 16]} style={{ marginTop: '16px' }}>
        <Col span={24}>
          <Card title="持仓明细">
            <Table
              dataSource={positions}
              columns={columns}
              rowKey="symbol"
              loading={loading}
              pagination={{ pageSize: 10 }}
              scroll={{ x: true }}
            />
          </Card>
        </Col>
      </Row>
    </div>
  );
};

export default PositionAnalysis;
