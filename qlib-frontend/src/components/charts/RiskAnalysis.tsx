import React from 'react';
import ReactECharts from 'echarts-for-react';
import { Card, Row, Col, Tabs, Statistic } from 'antd';
import type { RiskMetrics } from '../../types/backtest';

// 为 PortfolioChart 组件定义正确的数据接口
interface ChartPortfolioData {
  date: string[];
  strategy: number[];
  benchmark: number[];
}

// 扩展 RiskMetrics 接口，添加需要的属性
interface ExtendedRiskMetrics extends RiskMetrics {
  var95: number;
  var99: number;
  downSideRisk: number;
  trackingError: number;
  expectedShortfall: number;
}

interface RiskAnalysisProps {
  riskMetrics: ExtendedRiskMetrics;
  portfolioData: ChartPortfolioData;
  loading?: boolean;
}

// 修改组件类型定义，避免使用 React.FC
const RiskAnalysis = ({
  riskMetrics,
  portfolioData,
  loading = false
}: RiskAnalysisProps): JSX.Element => {
  // 计算收益率分布
  const calculateReturnsDistribution = () => {
    const returns = [];
    for (let i = 1; i < portfolioData.strategy.length; i++) {
      const dailyReturn = (portfolioData.strategy[i] / portfolioData.strategy[i - 1] - 1) * 100;
      returns.push(dailyReturn);
    }
    returns.sort((a, b) => a - b);

    // 计算直方图数据
    const binCount = 30;
    const min = Math.floor(Math.min(...returns));
    const max = Math.ceil(Math.max(...returns));
    const binWidth = (max - min) / binCount;
    const bins = Array(binCount).fill(0);
    const binRanges = Array(binCount).fill(0).map((_, i) => min + i * binWidth);

    returns.forEach(ret => {
      const binIndex = Math.min(
        Math.floor((ret - min) / binWidth),
        binCount - 1
      );
      bins[binIndex]++;
    });

    return {
      returns,
      bins,
      binRanges
    };
  };

  // 生成收益率分布图配置
  const getReturnsDistributionOption = () => {
    const { bins, binRanges } = calculateReturnsDistribution();
    return {
      title: {
        text: '日收益率分布',
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
        data: binRanges.map(v => v.toFixed(2) + '%'),
        axisLabel: {
          rotate: 45
        }
      },
      yAxis: {
        type: 'value'
      },
      series: [
        {
          name: '频次',
          type: 'bar',
          data: bins,
          itemStyle: {
            color: '#5470c6'
          }
        }
      ]
    };
  };

  // 生成风险指标雷达图配置
  const getRiskRadarOption = () => {
    const metrics = [
      { name: 'VaR(95%)', value: riskMetrics.var95 * 100 },
      { name: 'VaR(99%)', value: riskMetrics.var99 * 100 },
      { name: '期望损失', value: riskMetrics.expectedShortfall * 100 },
      { name: '下行风险', value: riskMetrics.downSideRisk * 100 },
      { name: '跟踪误差', value: riskMetrics.trackingError * 100 }
    ];

    return {
      title: {
        text: '风险指标雷达图',
        left: 'center'
      },
      tooltip: {
        trigger: 'item'
      },
      radar: {
        indicator: metrics.map(m => ({
          name: m.name,
          max: Math.ceil(Math.max(...metrics.map(m => m.value)) * 1.2)
        }))
      },
      series: [
        {
          type: 'radar',
          data: [
            {
              value: metrics.map(m => m.value),
              name: '风险指标',
              areaStyle: {
                color: 'rgba(84, 112, 198, 0.3)'
              },
              lineStyle: {
                color: '#5470c6'
              }
            }
          ]
        }
      ]
    };
  };

  // 计算滚动波动率
  const calculateRollingVolatility = () => {
    const window = 20; // 20天滚动窗口
    const volatilities = [];
    const dates = [];

    for (let i = window; i < portfolioData.strategy.length; i++) {
      const windowReturns = [];
      for (let j = i - window; j < i; j++) {
        const dailyReturn = portfolioData.strategy[j + 1] / portfolioData.strategy[j] - 1;
        windowReturns.push(dailyReturn);
      }
      
      // 计算标准差
      const mean = windowReturns.reduce((a, b) => a + b, 0) / window;
      const variance = windowReturns.reduce((a, b) => a + Math.pow(b - mean, 2), 0) / (window - 1);
      const volatility = Math.sqrt(variance * 252) * 100; // 年化波动率
      
      volatilities.push(volatility);
      dates.push(portfolioData.date[i]);
    }

    return { dates, volatilities };
  };

  // 生成滚动波动率图配置
  const getRollingVolatilityOption = () => {
    const { dates, volatilities } = calculateRollingVolatility();
    return {
      title: {
        text: '滚动波动率',
        left: 'center'
      },
      tooltip: {
        trigger: 'axis'
      },
      grid: {
        left: '3%',
        right: '4%',
        bottom: '3%',
        containLabel: true
      },
      xAxis: {
        type: 'category',
        data: dates,
        axisLabel: {
          rotate: 45
        }
      },
      yAxis: {
        type: 'value',
        axisLabel: {
          formatter: '{value}%'
        }
      },
      series: [
        {
          name: '波动率',
          type: 'line',
          data: volatilities,
          markLine: {
            data: [
              {
                type: 'average',
                name: '平均值'
              }
            ]
          }
        }
      ]
    };
  };

  return (
    <div className="risk-analysis">
      <Row gutter={[16, 16]}>
        <Col span={24}>
          <Card>
            <Row gutter={16}>
              <Col span={6}>
                <Statistic
                  title="VaR(95%)"
                  value={riskMetrics.var95 * 100}
                  precision={2}
                  suffix="%"
                />
              </Col>
              <Col span={6}>
                <Statistic
                  title="VaR(99%)"
                  value={riskMetrics.var99 * 100}
                  precision={2}
                  suffix="%"
                />
              </Col>
              <Col span={6}>
                <Statistic
                  title="期望损失"
                  value={riskMetrics.expectedShortfall * 100}
                  precision={2}
                  suffix="%"
                />
              </Col>
              <Col span={6}>
                <Statistic
                  title="跟踪误差"
                  value={riskMetrics.trackingError * 100}
                  precision={2}
                  suffix="%"
                />
              </Col>
            </Row>
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]} style={{ marginTop: '16px' }}>
        <Col span={24}>
          <Card>
            <Tabs
              items={[
                {
                  key: 'distribution',
                  label: '收益率分布',
                  children: (
                    <ReactECharts
                      option={getReturnsDistributionOption()}
                      style={{ height: '400px' }}
                      loading={loading}
                    />
                  )
                },
                {
                  key: 'radar',
                  label: '风险雷达',
                  children: (
                    <ReactECharts
                      option={getRiskRadarOption()}
                      style={{ height: '400px' }}
                      loading={loading}
                    />
                  )
                },
                {
                  key: 'volatility',
                  label: '滚动波动率',
                  children: (
                    <ReactECharts
                      option={getRollingVolatilityOption()}
                      style={{ height: '400px' }}
                      loading={loading}
                    />
                  )
                }
              ]}
            />
          </Card>
        </Col>
      </Row>
    </div>
  );
};

export default RiskAnalysis;
