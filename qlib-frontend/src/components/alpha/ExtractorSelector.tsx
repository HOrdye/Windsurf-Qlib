import React from 'react';
import { 
  Typography, 
  Row, 
  Col, 
  Card, 
  Radio, 
  Space,
  List
} from 'antd';
import { 
  FileTextOutlined, 
  RobotOutlined, 
  MergeCellsOutlined 
} from '@ant-design/icons';

const { Title, Text, Paragraph } = Typography;

// 组件属性接口定义
interface ExtractorSelectorProps {
  onExtractorSelected: (extractorType: string) => void;
  extractorType: string;
  documentContent: any;
}

/**
 * 提取器选择组件
 * 用于选择Alpha信号提取的方法
 */
const ExtractorSelector: React.FC<ExtractorSelectorProps> = ({ 
  onExtractorSelected, 
  extractorType,
  documentContent 
}) => {
  // 处理提取器类型变更
  const handleExtractorChange = (e: any) => {
    onExtractorSelected(e.target.value);
  };

  // 提取器选项配置
  const extractors = [
    {
      id: 'rule',
      name: '规则提取器',
      description: '使用预定义规则和模式识别从文档中提取Alpha因子信号。适用于结构化文档和标准格式的研报。',
      icon: <FileTextOutlined style={{ fontSize: 24 }} />,
      advantages: ['处理速度快', '无需外部API', '结果可预测'],
      limitations: ['仅适用于结构化文档', '难以处理复杂表达', '需要预定义规则']
    },
    {
      id: 'llm',
      name: 'LLM提取器',
      description: '使用大型语言模型(LLM)智能分析文档内容，提取Alpha因子信号。适用于非结构化文本和复杂表述。',
      icon: <RobotOutlined style={{ fontSize: 24 }} />,
      advantages: ['理解复杂语义', '处理非结构化文本', '提取隐含信息'],
      limitations: ['依赖外部API', '处理速度较慢', '可能产生幻觉']
    },
    {
      id: 'ensemble',
      name: '集成提取器',
      description: '结合规则提取和LLM提取的优势，通过多种方法提取信号并进行整合，提高提取质量和覆盖率。',
      icon: <MergeCellsOutlined style={{ fontSize: 24 }} />,
      advantages: ['提高信号质量', '增加信号覆盖', '减少单一方法局限'],
      limitations: ['计算资源消耗大', '处理时间最长', '配置复杂']
    }
  ];

  // 渲染文档摘要
  const renderDocumentSummary = () => {
    if (!documentContent) return null;

    return (
      <div style={{ marginBottom: 24 }}>
        <Title level={5}>文档摘要</Title>
        <Card style={{ maxHeight: 150, overflow: 'auto' }}>
          {documentContent.text ? (
            <Paragraph>
              {documentContent.text.substring(0, 300)}...
            </Paragraph>
          ) : (
            <Text type="secondary">
              无法显示文档摘要
            </Text>
          )}
        </Card>
      </div>
    );
  };

  return (
    <div>
      <Title level={5}>选择Alpha信号提取器</Title>
      
      {renderDocumentSummary()}
      
      <Radio.Group
        value={extractorType}
        onChange={handleExtractorChange}
        style={{ width: '100%' }}
      >
        <Row gutter={16}>
          {extractors.map((extractor) => (
            <Col xs={24} md={8} key={extractor.id}>
              <Card 
                hoverable
                style={{ 
                  height: '100%',
                  borderColor: extractorType === extractor.id ? '#1890ff' : undefined,
                  borderWidth: extractorType === extractor.id ? 2 : 1
                }}
                onClick={() => onExtractorSelected(extractor.id)}
              >
                <div style={{ display: 'flex', alignItems: 'center', marginBottom: 16 }}>
                  <Radio value={extractor.id} style={{ marginRight: 8 }} />
                  <span style={{ color: '#1890ff', marginRight: 8 }}>
                    {extractor.icon}
                  </span>
                  <Text strong>{extractor.name}</Text>
                </div>
                
                <Paragraph type="secondary" style={{ marginBottom: 16 }}>
                  {extractor.description}
                </Paragraph>
                
                <div>
                  <Text type="success" strong>优势:</Text>
                  <List
                    size="small"
                    dataSource={extractor.advantages}
                    renderItem={(item) => (
                      <List.Item style={{ padding: '4px 0' }}>
                        <Text>{item}</Text>
                      </List.Item>
                    )}
                  />
                  
                  <Text type="danger" strong style={{ marginTop: 8, display: 'block' }}>
                    局限:
                  </Text>
                  <List
                    size="small"
                    dataSource={extractor.limitations}
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
      
      <div style={{ marginTop: 16 }}>
        <Text type="secondary">
          注意: 选择提取器后，点击"下一步"按钮开始提取Alpha信号。根据文档大小和提取器类型，处理时间可能有所不同。
        </Text>
      </div>
    </div>
  );
};

export default ExtractorSelector;
