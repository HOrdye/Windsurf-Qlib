export interface PortfolioData {
  date: string;
  totalValue: number;
  cash: number;
  positionValue: number;
  returns: number;
}

export interface BacktestMetrics {
  annualizedReturn: number;
  annualizedVolatility: number;
  sharpeRatio: number;
  maxDrawdown: number;
  winRate: number;
}

export interface TradeRecord {
  tradeId: string;
  symbol: string;
  direction: 'BUY' | 'SELL';
  price: number;
  quantity: number;
  commission: number;
  tradeTime: string;
}

export interface Position {
  symbol: string;
  quantity: number;
  costPrice: number;
  marketValue: number;
}

export interface RiskMetrics {
  valueAtRisk: number;
  expectedShortfall: number;
  beta: number;
}

export interface BacktestResult {
  portfolioData: PortfolioData[];
  metrics: BacktestMetrics;
  trades: TradeRecord[];
  positions: Position[];
  riskMetrics: RiskMetrics;
}
