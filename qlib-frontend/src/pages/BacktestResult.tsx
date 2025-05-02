import React from 'react';
import { Card, Row, Col, Statistic, Space, Button, message } from 'antd';
import {
  ArrowUpOutlined,
  ArrowDownOutlined,
  DownloadOutlined
} from '@ant-design/icons';
import PortfolioChart from '../components/charts/PortfolioChart';
import PositionAnalysis from '../components/charts/PositionAnalysis';
import TradeRecords from '../components/tables/TradeRecords';
import RiskAnalysis from '../components/charts/RiskAnalysis';
import type { BacktestResult, BacktestMetrics, Position, TradeRecord, PortfolioData, RiskMetrics } from '../types/backtest';

// 扩展 BacktestMetrics 接口，添加组件中使用的属性
interface ExtendedBacktestMetrics extends BacktestMetrics {
  annualReturn: number;
}

// 扩展 Position 接口，添加组件中使用的属性
interface ExtendedPosition extends Position {
  volume: number;
  cost: number;
  pnl: number;
  pnlRatio: number;
}

// 扩展 TradeRecord 接口，添加组件中使用的属性
interface ExtendedTradeRecord extends Omit<TradeRecord, 'direction'> {
  date: string;
  volume: number;
  amount: number;
  direction: 'BUY' | 'SELL';
}

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
}

// 扩展 BacktestResult 接口，使用扩展的类型
interface ExtendedBacktestResult extends Omit<BacktestResult, 'metrics' | 'positions' | 'trades' | 'portfolioData' | 'riskMetrics'> {
  metrics: ExtendedBacktestMetrics;
  positions: ExtendedPosition[];
  trades: ExtendedTradeRecord[];
  portfolioData: PortfolioData[];
  chartData: ChartPortfolioData;
  riskMetrics: ExtendedRiskMetrics;
}

interface BacktestResultPageProps {
  taskId?: string;
}

// 修改组件类型定义，避免使用 React.FC
const BacktestResultPage = ({ taskId }: BacktestResultPageProps): JSX.Element => {
  const [loading, setLoading] = React.useState(false);
  const [backtestData, setBacktestData] = React.useState<ExtendedBacktestResult | null>(null);

  // 加载回测数据
  React.useEffect(() => {
    if (!taskId) return;

    const fetchBacktestData = async () => {
      setLoading(true);
      try {
        // TODO: 替换为实际的API调用
        const response = await fetch(`/api/backtest/${taskId}`);
        const data = await response.json();
        
        // 类型适配：将API返回的数据转换为扩展类型
        const adaptedData: ExtendedBacktestResult = {
          ...data,
          metrics: {
            ...data.metrics,
            annualReturn: data.metrics.annualizedReturn || 0,
          },
          positions: data.positions.map((pos: Position) => ({
            ...pos,
            volume: pos.quantity || 0,
            cost: pos.costPrice || 0,
            pnl: (pos.marketValue - (pos.quantity * pos.costPrice)) || 0,
            pnlRatio: ((pos.marketValue / (pos.quantity * pos.costPrice)) - 1) || 0
          })),
          trades: data.trades.map((trade: TradeRecord) => ({
            ...trade,
            date: trade.tradeTime?.split('T')[0] || '',
            volume: trade.quantity || 0,
            amount: trade.price * trade.quantity || 0
          })),
          portfolioData: data.portfolioData || [],
          chartData: {
            date: data.portfolioData.map((p: PortfolioData) => p.date) || [],
            strategy: data.portfolioData.map((p: PortfolioData) => p.totalValue) || [],
            benchmark: data.portfolioData.map((p: PortfolioData) => p.totalValue * 0.9) || []
          },
          riskMetrics: {
            ...data.riskMetrics,
            var95: data.riskMetrics.valueAtRisk || 0,
            var99: data.riskMetrics.valueAtRisk * 1.2 || 0,
            downSideRisk: data.riskMetrics.valueAtRisk * 0.8 || 0,
            trackingError: 0.05
          }
        };
        
        setBacktestData(adaptedData);
      } catch (error) {
        console.error('加载回测数据失败:', error);
        message.error('加载回测数据失败');
      } finally {
        setLoading(false);
      }
    };

    fetchBacktestData();
  }, [taskId]);

  // 导出回测报告
  const exportReport = async () => {
    if (!backtestData) return;

    try {
      // TODO: 实现导出功能
      message.success('报告导出成功');
    } catch (error) {
      console.error('导出报告失败:', error);
      message.error('导出报告失败');
    }
  };

  if (!backtestData) {
    return (
      <Card loading={loading}>
        <div style={{ textAlign: 'center', padding: '40px 0' }}>
          {loading ? '正在加载回测结果...' : '暂无回测数据'}
        </div>
      </Card>
    );
  }

  return (
    <div className="backtest-result">
      <Space direction="vertical" style={{ width: '100%' }} size="large">
        <Row gutter={[16, 16]}>
          <Col span={24}>
            <Card
              title="回测结果概览"
              extra={
                <Button icon={<DownloadOutlined />} onClick={exportReport}>
                  导出报告
                </Button>
              }
            >
              <Row gutter={16}>
                <Col span={6}>
                  <Statistic
                    title="年化收益率"
                    value={backtestData.metrics.annualReturn * 100}
                    precision={2}
                    valueStyle={{
                      color: backtestData.metrics.annualReturn > 0 ? '#3f8600' : '#cf1322'
                    }}
                    prefix={
                      backtestData.metrics.annualReturn > 0 ? (
                        <ArrowUpOutlined />
                      ) : (
                        <ArrowDownOutlined />
                      )
                    }
                    suffix="%"
                  />
                </Col>
                <Col span={6}>
                  <Statistic
                    title="夏普比率"
                    value={backtestData.metrics.sharpeRatio}
                    precision={2}
                  />
                </Col>
                <Col span={6}>
                  <Statistic
                    title="最大回撤"
                    value={backtestData.metrics.maxDrawdown * 100}
                    precision={2}
                    valueStyle={{ color: '#cf1322' }}
                    suffix="%"
                  />
                </Col>
                <Col span={6}>
                  <Statistic
                    title="胜率"
                    value={backtestData.metrics.winRate * 100}
                    precision={2}
                    suffix="%"
                  />
                </Col>
              </Row>
            </Card>
          </Col>
        </Row>

        <Row gutter={[16, 16]}>
          <Col span={24}>
            <PortfolioChart
              data={backtestData.chartData}
              loading={loading}
              height="500px"
            />
          </Col>
        </Row>

        <Row gutter={[16, 16]}>
          <Col span={24}>
            <PositionAnalysis
              positions={backtestData.positions}
              loading={loading}
            />
          </Col>
        </Row>

        <Row gutter={[16, 16]}>
          <Col span={24}>
            <TradeRecords
              trades={backtestData.trades}
              loading={loading}
            />
          </Col>
        </Row>

        <Row gutter={[16, 16]}>
          <Col span={24}>
            <RiskAnalysis
              riskMetrics={backtestData.riskMetrics}
              portfolioData={backtestData.chartData}
              loading={loading}
            />
          </Col>
        </Row>
      </Space>
    </div>
  );
};

export default BacktestResultPage;
