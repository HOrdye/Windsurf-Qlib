import React, { useState } from 'react';
import { 
  Typography, 
  Row, 
  Col, 
  Card, 
  Table, 
  Button, 
  Tag, 
  Tooltip, 
  Collapse, 
  Space,
  Divider,
  Progress,
  Alert,
  Statistic
} from 'antd';
import { 
  ArrowUpOutlined, 
  ArrowDownOutlined, 
  MinusOutlined,
  DownOutlined,
  UpOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  WarningOutlined,
  DownloadOutlined
} from '@ant-design/icons';

const { Title, Text, Paragraph } = Typography;
const { Panel } = Collapse;

// 组件属性接口定义
interface SignalResultsProps {
  signals: any[];
  validationResults: any[];
  onExportToCsv: () => void;
}

/**
 * 信号结果组件
 * 用于展示验证后的Alpha信号结果和指标
 */
const SignalResults: React.FC<SignalResultsProps> = ({
  signals,
  validationResults,
  onExportToCsv
}) => {
  // 状态管理
  const [expandedSignal, setExpandedSignal] = useState<string | null>(null);

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

  // 获取验证状态图标和颜色
  const getValidationStatusInfo = (status: string) => {
    switch (status) {
      case 'passed':
        return { icon: <CheckCircleOutlined />, color: 'success' };
      case 'failed':
        return { icon: <CloseCircleOutlined />, color: 'error' };
      case 'warning':
        return { icon: <WarningOutlined />, color: 'warning' };
      default:
        return { icon: <WarningOutlined />, color: 'default' };
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

  // 获取信号的验证结果
  const getSignalValidationResult = (signalId: string) => {
    return validationResults.find(result => result.signal_id === signalId) || null;
  };

  // 渲染验证结果详情
  const renderValidationDetails = (validationResult: any) => {
    if (!validationResult) return null;

    return (
      <div style={{ marginTop: 16 }}>
        <Title level={5}>验证结果详情:</Title>
        
        {validationResult.issues && validationResult.issues.length > 0 ? (
          <div style={{ marginBottom: 16 }}>
            <Text>发现的问题:</Text>
            <div style={{ marginTop: 8 }}>
              {validationResult.issues.map((issue: any, index: number) => (
                <Alert 
                  key={index} 
                  message={issue.message}
                  type={issue.severity || 'warning'} 
                  style={{ marginBottom: 8 }}
                />
              ))}
            </div>
          </div>
        ) : (
          <Alert 
            message="未发现问题，信号验证通过" 
            type="success" 
            style={{ marginBottom: 16 }} 
          />
        )}
        
        {validationResult.metrics && Object.keys(validationResult.metrics).length > 0 && (
          <div>
            <Title level={5}>性能指标:</Title>
            <Row gutter={[16, 16]}>
              {Object.entries(validationResult.metrics).map(([key, value]: [string, any], index) => (
                <Col span={8} key={index}>
                  <Card size="small">
                    <Statistic 
                      title={key}
                      value={typeof value === 'number' ? value.toFixed(4) : value}
                      precision={4}
                    />
                  </Card>
                </Col>
              ))}
            </Row>
          </div>
        )}
        
        {validationResult.recommendations && validationResult.recommendations.length > 0 && (
          <div style={{ marginTop: 16 }}>
            <Title level={5}>改进建议:</Title>
            <ul>
              {validationResult.recommendations.map((rec: string, index: number) => (
                <li key={index}>
                  <Text>{rec}</Text>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    );
  };

  // 渲染信号详情
  const renderSignalDetails = (signal: any) => {
    const validationResult = getSignalValidationResult(signal.id);
    
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
          
          <Col span={24}>
            <Divider style={{ margin: '16px 0' }} />
            {renderValidationDetails(validationResult)}
          </Col>
        </Row>
      </div>
    );
  };

  // 计算验证统计信息
  const getValidationStats = () => {
    if (!validationResults || validationResults.length === 0) {
      return { passed: 0, failed: 0, warning: 0, total: 0 };
    }
    
    const passed = validationResults.filter(result => result.status === 'passed').length;
    const failed = validationResults.filter(result => result.status === 'failed').length;
    const warning = validationResults.filter(result => result.status === 'warning').length;
    
    return {
      passed,
      failed,
      warning,
      total: validationResults.length
    };
  };

  // 验证统计信息
  const stats = getValidationStats();

  // 表格列定义
  const columns = [
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
      title: '验证状态',
      key: 'validation',
      render: (_, record: any) => {
        const validationResult = getSignalValidationResult(record.id);
        const status = validationResult ? validationResult.status : 'unknown';
        const statusInfo = getValidationStatusInfo(status);
        
        return (
          <Tag icon={statusInfo.icon} color={statusInfo.color}>
            {status === 'passed' ? '通过' :
             status === 'failed' ? '失败' :
             status === 'warning' ? '警告' : '未验证'}
          </Tag>
        );
      }
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
      <Title level={5}>Alpha信号结果</Title>
      
      <Row gutter={[16, 24]}>
        <Col xs={24} md={16}>
          <Card title="验证结果摘要">
            <Row gutter={16}>
              <Col span={8}>
                <Statistic 
                  title="通过"
                  value={stats.passed}
                  valueStyle={{ color: '#52c41a' }}
                />
              </Col>
              <Col span={8}>
                <Statistic 
                  title="警告"
                  value={stats.warning}
                  valueStyle={{ color: '#faad14' }}
                />
              </Col>
              <Col span={8}>
                <Statistic 
                  title="失败"
                  value={stats.failed}
                  valueStyle={{ color: '#f5222d' }}
                />
              </Col>
            </Row>
            
            <div style={{ marginTop: 16 }}>
              <Text>总体验证进度:</Text>
              <Progress 
                percent={stats.total > 0 ? Math.round((stats.passed / stats.total) * 100) : 0}
                status="active"
                style={{ marginTop: 8 }}
              />
              <Text type="secondary">
                {stats.total > 0 ? Math.round((stats.passed / stats.total) * 100) : 0}% 的信号通过验证
              </Text>
            </div>
          </Card>
        </Col>
        
        <Col xs={24} md={8}>
          <Card title="导出结果" style={{ height: '100%' }}>
            <div style={{ display: 'flex', flexDirection: 'column', justifyContent: 'center', height: '100%' }}>
              <Paragraph style={{ marginBottom: 16 }}>
                将验证后的Alpha信号导出为CSV格式，用于进一步分析或回测
              </Paragraph>
              <Button
                type="primary"
                icon={<DownloadOutlined />}
                onClick={onExportToCsv}
                size="large"
                block
              >
                导出为CSV
              </Button>
            </div>
          </Card>
        </Col>
      </Row>
      
      <div style={{ marginTop: 24 }}>
        <Title level={5}>验证后的信号 ({signals.length})</Title>
        
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
      
      <div style={{ marginTop: 16 }}>
        <Text type="secondary">
          注意: 您可以点击每个信号旁边的展开按钮查看详细信息，包括验证结果和性能指标。
          使用"导出为CSV"按钮将验证后的信号导出为CSV格式，用于进一步分析或回测。
        </Text>
      </div>
    </div>
  );
};

export default SignalResults;
