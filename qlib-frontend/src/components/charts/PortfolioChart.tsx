import React from 'react';
import { EChartsOption } from 'echarts/types/dist/shared';
import { Card, Radio, DatePicker, Space, Button } from 'antd';
import { RadioChangeEvent } from 'antd/lib/radio';
import { saveAs } from 'file-saver';
import * as XLSX from 'xlsx';
import ReactECharts from 'echarts-for-react';

const { RangePicker } = DatePicker;

interface PortfolioData {
  date: string[];
  strategy: number[];
  benchmark: number[];
}

interface PortfolioChartProps {
  data: PortfolioData;
  title?: string;
  height?: number | string;
  loading?: boolean;
}

const PortfolioChart = ({
  data,
  title = '策略净值曲线',
  height = '400px',
  loading = false
}: PortfolioChartProps): JSX.Element => {
  const [chartType, setChartType] = React.useState<'line' | 'bar'>('line');
  const [dateRange, setDateRange] = React.useState<[string, string] | null>(null);

  // 处理数据范围过滤
  const filterDataByRange = (data: PortfolioData, range: [string, string] | null) => {
    if (!range) return data;

    const [start, end] = range;
    const startIndex = data.date.findIndex(d => d >= start);
    const endIndex = data.date.findIndex(d => d > end) - 1;

    return {
      date: data.date.slice(startIndex, endIndex + 1),
      strategy: data.strategy.slice(startIndex, endIndex + 1),
      benchmark: data.benchmark.slice(startIndex, endIndex + 1),
    };
  };

  // 计算最大回撤
  const calculateMaxDrawdown = (values: number[]): number => {
    let maxDrawdown = 0;
    let peak = values[0];

    for (let i = 1; i < values.length; i++) {
      if (values[i] > peak) {
        peak = values[i];
      } else {
        const drawdown = (peak - values[i]) / peak;
        maxDrawdown = Math.max(maxDrawdown, drawdown);
      }
    }

    return maxDrawdown;
  };

  // 计算年化收益率
  const calculateAnnualReturn = (values: number[]): number => {
    const totalReturn = values[values.length - 1] / values[0] - 1;
    const years = data.date.length / 252; // 假设252个交易日
    return Math.pow(1 + totalReturn, 1 / years) - 1;
  };

  // 导出数据为Excel
  const exportToExcel = () => {
    const filteredData = filterDataByRange(data, dateRange);
    const worksheet = XLSX.utils.aoa_to_sheet([
      ['日期', '策略净值', '基准净值'],
      ...filteredData.date.map((date, index) => [
        date,
        filteredData.strategy[index],
        filteredData.benchmark[index]
      ])
    ]);

    const workbook = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(workbook, worksheet, '净值数据');
    const excelBuffer = XLSX.write(workbook, { bookType: 'xlsx', type: 'array' });
    const blob = new Blob([excelBuffer], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' });
    saveAs(blob, `portfolio_data_${new Date().toISOString().slice(0, 10)}.xlsx`);
  };

  // 生成图表配置
  const getChartOption = (): EChartsOption => {
    const filteredData = filterDataByRange(data, dateRange);
    const strategyDrawdown = calculateMaxDrawdown(filteredData.strategy);
    const benchmarkDrawdown = calculateMaxDrawdown(filteredData.benchmark);
    const strategyReturn = calculateAnnualReturn(filteredData.strategy);
    const benchmarkReturn = calculateAnnualReturn(filteredData.benchmark);

    return {
      title: {
        text: title,
        left: 'center'
      },
      tooltip: {
        trigger: 'axis',
        axisPointer: {
          type: 'cross'
        }
      },
      legend: {
        data: [
          `策略 (年化${(strategyReturn * 100).toFixed(2)}%, 最大回撤${(strategyDrawdown * 100).toFixed(2)}%)`,
          `基准 (年化${(benchmarkReturn * 100).toFixed(2)}%, 最大回撤${(benchmarkDrawdown * 100).toFixed(2)}%)`
        ],
        bottom: 10
      },
      grid: {
        left: '3%',
        right: '4%',
        bottom: '15%',
        containLabel: true
      },
      xAxis: {
        type: 'category',
        data: filteredData.date,
        axisLabel: {
          rotate: 30
        }
      },
      yAxis: {
        type: 'value',
        axisLabel: {
          formatter: '{value}'
        }
      },
      series: [
        {
          name: `策略 (年化${(strategyReturn * 100).toFixed(2)}%, 最大回撤${(strategyDrawdown * 100).toFixed(2)}%)`,
          type: chartType,
          data: filteredData.strategy,
          smooth: true,
          lineStyle: {
            width: 2
          }
        },
        {
          name: `基准 (年化${(benchmarkReturn * 100).toFixed(2)}%, 最大回撤${(benchmarkDrawdown * 100).toFixed(2)}%)`,
          type: chartType,
          data: filteredData.benchmark,
          smooth: true,
          lineStyle: {
            width: 2
          }
        }
      ],
      dataZoom: [
        {
          type: 'inside',
          start: 0,
          end: 100
        },
        {
          show: true,
          type: 'slider',
          bottom: 60,
          start: 0,
          end: 100
        }
      ]
    };
  };

  return (
    <Card>
      <Space direction="vertical" style={{ width: '100%', marginBottom: 16 }}>
        <Space>
          <Radio.Group
            value={chartType}
            onChange={(e: RadioChangeEvent) => setChartType(e.target.value)}
          >
            <Radio.Button value="line">折线图</Radio.Button>
            <Radio.Button value="bar">柱状图</Radio.Button>
          </Radio.Group>
          <RangePicker
            onChange={(dates) => {
              if (dates) {
                setDateRange([
                  dates[0]!.format('YYYY-MM-DD'),
                  dates[1]!.format('YYYY-MM-DD')
                ]);
              } else {
                setDateRange(null);
              }
            }}
          />
          <Button onClick={exportToExcel}>导出Excel</Button>
        </Space>
      </Space>
      <ReactECharts
        option={getChartOption()}
        style={{ height }}
        loading={loading}
        notMerge={true}
      />
    </Card>
  );
};

export default PortfolioChart;
