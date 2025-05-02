import React, { useState } from 'react';
import { 
  Typography, 
  Row, 
  Col, 
  Card, 
  Table, 
  Checkbox, 
  Radio, 
  Tag, 
  Tooltip, 
  Button, 
  Collapse, 
  Space,
  List
} from 'antd';
import { 
  ArrowUpOutlined, 
  ArrowDownOutlined, 
  MinusOutlined,
  DownOutlined,
  UpOutlined,
  InfoCircleOutlined
} from '@ant-design/icons';

const { Title, Text, Paragraph } = Typography;
const { Panel } = Collapse;

// 组件属性接口定义
interface SignalValidatorProps {
  signals: any[];
  onSignalSelection: (selectedIds: string[]) => void;
  selectedSignalIds: string[];
  onValidatorSelected: (validatorType: string) => void;
  validatorType: string;
}

/**
 * 信号验证组件
 * 用于显示提取的Alpha信号并选择验证方法
 */
const SignalValidator: React.FC<SignalValidatorProps> = ({
  signals,
  onSignalSelection,
  selectedSignalIds,
  onValidatorSelected,
  validatorType
}) => {
  // 状态管理
  const [expandedSignal, setExpandedSignal] = useState<string | null>(null);

  // 处理验证器类型变更
  const handleValidatorChange = (e: any) => {
    onValidatorSelected(e.target.value);
  };

  // 处理信号选择变更
  const handleSignalSelect = (signalId: string) => {
    const isSelected = selectedSignalIds.includes(signalId);
    let newSelectedIds: string[];
    
    if (isSelected) {
      newSelectedIds = selectedSignalIds.filter(id => id !== signalId);
    } else {
      newSelectedIds = [...selectedSignalIds, signalId];
    }
    
    onSignalSelection(newSelectedIds);
  };

  // 处理全选/取消全选
  const handleSelectAll = (e: any) => {
    if (e.target.checked) {
      onSignalSelection(signals.map(signal => signal.id));
    } else {
      onSignalSelection([]);
    }
  };

  // 处理信号详情展开/折叠
  const handleExpandSignal = (signalId: string) => {
    setExpandedSignal(expandedSignal === signalId ? null : signalId);
  };

  // 获取信号方向图标
  const getDirectionIcon = (direction: string) => {
    switch (direction) {
      case 'positive':
        return <ArrowUpOutlined style={{ color: '#52c41a' }} />;
      case 'negative':
        return <ArrowDownOutlined style={{ color: '#f5222d' }} />;
      default:
        return <MinusOutlined style={{ color: '#8c8c8c' }} />;
    }
  };

  // 获取信号类型标签颜色
  const getSignalTypeColor = (type: string) => {
    switch (type) {
      case 'fundamental':
        return 'blue';
      case 'technical':
        return 'purple';
      case 'sentiment':
        return 'orange';
      case 'macro':
        return 'cyan';
      default:
        return 'default';
    }
  };

  // 获取时间范围标签颜色
  const getTimeHorizonColor = (horizon: string) => {
    switch (horizon) {
      case 'short_term':
        return 'red';
      case 'medium_term':
        return 'orange';
      case 'long_term':
        return 'green';
      default:
        return 'default';
    }
  };

  // 渲染信号详情
  const renderSignalDetails = (signal: any) => {
    return (
      <div style={{ padding: 16, backgroundColor: '#f5f5f5', display: expandedSignal === signal.id ? 'block' : 'none' }}>
        <Row gutter={16}>
          <Col xs={24} md={12}>
            <Title level={5}>详细描述:</Title>
            <Paragraph>{signal.description}</Paragraph>
            
            {signal.stock_codes && signal.stock_codes.length > 0 && (
              <div style={{ marginTop: 16 }}>
                <Title level={5}>相关股票:</Title>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
                  {signal.stock_codes.map((code: string) => (
                    <Tag key={code}>{code}</Tag>
                  ))}
                </div>
              </div>
            )}
            
            {signal.industry && (
              <div style={{ marginTop: 16 }}>
                <Title level={5}>行业:</Title>
                <Paragraph>{signal.industry}</Paragraph>
              </div>
            )}
          </Col>
          
          <Col xs={24} md={12}>
            {signal.metrics && Object.keys(signal.metrics).length > 0 && (
              <div>
                <Title level={5}>相关指标:</Title>
                <Table 
                  size="small"
                  pagination={false}
                  dataSource={Object.entries(signal.metrics).map(([key, value]: [string, any], index) => ({
                    key: index,
                    metric: key,
                    value: value
                  }))}
                  columns={[
                    { title: '指标', dataIndex: 'metric' },
                    { title: '值', dataIndex: 'value', align: 'right' }
                  ]}
                />
              </div>
            )}
            
            <div style={{ marginTop: 16 }}>
              <Title level={5}>信号元数据:</Title>
              <Row gutter={[8, 8]}>
                <Col span={12}>
                  <Text type="secondary">
                    信号类型: {signal.signal_type || '未指定'}
                  </Text>
                </Col>
                <Col span={12}>
                  <Text type="secondary">
                    因子类别: {signal.factor_category || '未指定'}
                  </Text>
                </Col>
                <Col span={12}>
                  <Text type="secondary">
                    置信度: {(signal.confidence * 100).toFixed(0)}%
                  </Text>
                </Col>
                <Col span={12}>
                  <Text type="secondary">
                    来源: {signal.source || '未知'}
                  </Text>
                </Col>
              </Row>
            </div>
          </Col>
        </Row>
      </div>
    );
  };

  // 验证器选项配置
  const validators = [
    {
      id: 'basic',
      name: '基础验证器',
      description: '验证信号的基本格式、完整性和一致性，确保信号包含所有必要字段并符合预期格式。',
      advantages: ['快速验证', '无需历史数据', '适用于所有信号类型']
    },
    {
      id: 'backtest',
      name: '回测验证器',
      description: '使用历史市场数据对信号进行回测验证，评估信号在历史数据上的表现和预测能力。',
      advantages: ['提供实证支持', '评估信号质量', '计算关键绩效指标']
    }
  ];

  // 表格列定义
  const columns = [
    {
      title: <Checkbox 
              indeterminate={selectedSignalIds.length > 0 && selectedSignalIds.length < signals.length}
              checked={signals.length > 0 && selectedSignalIds.length === signals.length}
              onChange={handleSelectAll}
            />,
      dataIndex: 'id',
      key: 'selection',
      width: 50,
      render: (id: string) => (
        <Checkbox
          checked={selectedSignalIds.includes(id)}
          onChange={() => handleSignalSelect(id)}
        />
      )
    },
    {
      title: '信号名称',
      dataIndex: 'name',
      key: 'name',
      render: (text: string) => <Text strong>{text}</Text>
    },
    {
      title: '类型',
      dataIndex: 'signal_type',
      key: 'type',
      render: (type: string) => (
        <Tag color={getSignalTypeColor(type)}>
          {type || '未知'}
        </Tag>
      )
    },
    {
      title: '方向',
      dataIndex: 'direction',
      key: 'direction',
      render: (direction: string) => (
        <Space>
          {getDirectionIcon(direction)}
          <Text>
            {direction === 'positive' ? '正向' : 
             direction === 'negative' ? '负向' : '中性'}
          </Text>
        </Space>
      )
    },
    {
      title: '时间范围',
      dataIndex: 'time_horizon',
      key: 'time_horizon',
      render: (horizon: string) => (
        <Tag color={getTimeHorizonColor(horizon)}>
          {horizon === 'short_term' ? '短期' :
           horizon === 'medium_term' ? '中期' :
           horizon === 'long_term' ? '长期' : '未知'}
        </Tag>
      )
    },
    {
      title: '置信度',
      dataIndex: 'confidence',
      key: 'confidence',
      render: (confidence: number) => (
        <Text>{(confidence * 100).toFixed(0)}%</Text>
      )
    },
    {
      title: '详情',
      key: 'details',
      render: (_, record: any) => (
        <Button 
          type="text" 
          icon={expandedSignal === record.id ? <UpOutlined /> : <DownOutlined />}
          onClick={() => handleExpandSignal(record.id)}
        />
      )
    }
  ];

  return (
    <div>
      <Title level={5}>验证Alpha信号</Title>
      
      <div style={{ marginBottom: 24 }}>
        <Title level={5}>提取的信号 ({signals.length})</Title>
        
        <Table
          columns={columns}
          dataSource={signals.map(signal => ({ ...signal, key: signal.id }))}
          pagination={false}
          expandable={{
            expandedRowRender: renderSignalDetails,
            expandedRowKeys: expandedSignal ? [expandedSignal] : [],
            onExpand: (expanded, record) => handleExpandSignal(record.id)
          }}
          locale={{ emptyText: '未找到任何Alpha信号' }}
        />
      </div>
      
      <div style={{ marginBottom: 16 }}>
        <Title level={5}>
          选择验证方法
          <Tooltip title="验证方法决定了如何评估提取的Alpha信号质量和可靠性">
            <InfoCircleOutlined style={{ marginLeft: 8 }} />
          </Tooltip>
        </Title>
        
        <Radio.Group
          value={validatorType}
          onChange={handleValidatorChange}
        >
          <Row gutter={16}>
            {validators.map((validator) => (
              <Col xs={24} md={12} key={validator.id}>
                <Card>
                  <div style={{ marginBottom: 8 }}>
                    <Radio value={validator.id}>
                      <Text strong>{validator.name}</Text>
                    </Radio>
                  </div>
                  <Paragraph type="secondary">
                    {validator.description}
                  </Paragraph>
                  <div style={{ marginTop: 16 }}>
                    <Text type="success" strong>优势:</Text>
                    <List
                      size="small"
                      dataSource={validator.advantages}
                      renderItem={(item) => (
                        <List.Item style={{ padding: '4px 0' }}>
                          <Text>{item}</Text>
                        </List.Item>
                      )}
                    />
                  </div>
                </Card>
              </Col>
            ))}
          </Row>
        </Radio.Group>
      </div>
      
      <div style={{ marginTop: 16 }}>
        <Text type="secondary">
          注意: 选择要验证的信号和验证方法后，点击"下一步"按钮开始验证过程。
          回测验证需要访问历史数据，可能需要较长处理时间。
        </Text>
      </div>
    </div>
  );
};

export default SignalValidator;
