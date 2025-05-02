import React from 'react';
import { Card, Table, DatePicker, Space, Button, Tag } from 'antd';
import type { TradeRecord } from '../../types/backtest';
import { DownloadOutlined } from '@ant-design/icons';
import * as XLSX from 'xlsx';
import { saveAs } from 'file-saver';

const { RangePicker } = DatePicker;

// 扩展 TradeRecord 接口，添加组件中使用的属性
interface ExtendedTradeRecord extends Omit<TradeRecord, 'direction'> {
  date: string;
  volume: number;
  amount: number;
  direction: 'BUY' | 'SELL'; // 使用大写形式，与 TradeRecord 类型定义一致
}

interface TradeRecordsProps {
  trades: ExtendedTradeRecord[];
  loading?: boolean;
}

// 修改组件类型定义，避免使用 React.FC
const TradeRecords = ({
  trades,
  loading = false
}: TradeRecordsProps): JSX.Element => {
  const [dateRange, setDateRange] = React.useState<[string, string] | null>(null);
  const [filteredTrades, setFilteredTrades] = React.useState(trades);

  // 处理日期范围变化
  React.useEffect(() => {
    if (!dateRange) {
      setFilteredTrades(trades);
      return;
    }

    const [startDate, endDate] = dateRange;
    const filtered = trades.filter(
      trade => trade.date >= startDate && trade.date <= endDate
    );
    setFilteredTrades(filtered);
  }, [dateRange, trades]);

  // 导出交易记录
  const exportToExcel = () => {
    const worksheet = XLSX.utils.json_to_sheet(filteredTrades.map(trade => ({
      日期: trade.date,
      股票代码: trade.symbol,
      方向: trade.direction === 'BUY' ? '买入' : '卖出',
      价格: trade.price,
      数量: trade.volume,
      金额: trade.amount,
      手续费: trade.commission
    })));

    const workbook = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(workbook, worksheet, '交易记录');
    const excelBuffer = XLSX.write(workbook, { bookType: 'xlsx', type: 'array' });
    const blob = new Blob([excelBuffer], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' });
    saveAs(blob, `trade_records_${new Date().toISOString().slice(0, 10)}.xlsx`);
  };

  // 计算统计数据
  const calculateStats = () => {
    const stats = filteredTrades.reduce(
      (acc, trade) => {
        if (trade.direction === 'BUY') {
          acc.totalBuy += trade.amount;
          acc.buyCount++;
        } else {
          acc.totalSell += trade.amount;
          acc.sellCount++;
        }
        acc.totalCommission += trade.commission;
        return acc;
      },
      { totalBuy: 0, totalSell: 0, buyCount: 0, sellCount: 0, totalCommission: 0 }
    );

    return [
      { label: '买入次数', value: stats.buyCount },
      { label: '卖出次数', value: stats.sellCount },
      { label: '买入金额', value: stats.totalBuy.toFixed(2) },
      { label: '卖出金额', value: stats.totalSell.toFixed(2) },
      { label: '总手续费', value: stats.totalCommission.toFixed(2) },
    ];
  };

  const columns = [
    {
      title: '日期',
      dataIndex: 'date',
      key: 'date',
      sorter: (a: ExtendedTradeRecord, b: ExtendedTradeRecord) => a.date.localeCompare(b.date),
    },
    {
      title: '股票代码',
      dataIndex: 'symbol',
      key: 'symbol',
    },
    {
      title: '方向',
      dataIndex: 'direction',
      key: 'direction',
      render: (direction: 'BUY' | 'SELL') => (
        <Tag color={direction === 'BUY' ? 'green' : 'red'}>
          {direction === 'BUY' ? '买入' : '卖出'}
        </Tag>
      ),
      filters: [
        { text: '买入', value: 'BUY' },
        { text: '卖出', value: 'SELL' },
      ],
      onFilter: (value: string, record: ExtendedTradeRecord) => record.direction === value,
    },
    {
      title: '价格',
      dataIndex: 'price',
      key: 'price',
      render: (value: number) => value.toFixed(3),
      sorter: (a: ExtendedTradeRecord, b: ExtendedTradeRecord) => a.price - b.price,
    },
    {
      title: '数量',
      dataIndex: 'volume',
      key: 'volume',
      render: (value: number) => value.toLocaleString(),
      sorter: (a: ExtendedTradeRecord, b: ExtendedTradeRecord) => a.volume - b.volume,
    },
    {
      title: '金额',
      dataIndex: 'amount',
      key: 'amount',
      render: (value: number) => value.toFixed(2),
      sorter: (a: ExtendedTradeRecord, b: ExtendedTradeRecord) => a.amount - b.amount,
    },
    {
      title: '手续费',
      dataIndex: 'commission',
      key: 'commission',
      render: (value: number) => value.toFixed(2),
      sorter: (a: ExtendedTradeRecord, b: ExtendedTradeRecord) => a.commission - b.commission,
    },
  ];

  const stats = calculateStats();

  return (
    <Card
      title="交易记录"
      extra={
        <Space>
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
          <Button
            icon={<DownloadOutlined />}
            onClick={exportToExcel}
          >
            导出Excel
          </Button>
        </Space>
      }
    >
      <Space direction="vertical" style={{ width: '100%' }} size="large">
        <div style={{ display: 'flex', justifyContent: 'space-around', padding: '16px 0' }}>
          {stats.map((stat, index) => (
            <div key={index} style={{ textAlign: 'center' }}>
              <div style={{ fontSize: '12px', color: '#8c8c8c' }}>{stat.label}</div>
              <div style={{ fontSize: '16px', fontWeight: 'bold' }}>{stat.value}</div>
            </div>
          ))}
        </div>

        <Table
          dataSource={filteredTrades}
          columns={columns}
          rowKey={(record) => `${record.date}-${record.symbol}-${record.direction}`}
          loading={loading}
          pagination={{
            pageSize: 10,
            showSizeChanger: true,
            showTotal: (total) => `共 ${total} 条记录`,
          }}
          scroll={{ x: true }}
        />
      </Space>
    </Card>
  );
};

export default TradeRecords;
