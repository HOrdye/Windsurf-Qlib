import React from 'react';
import { Typography, Card, Tabs } from 'antd';
import AlphaGeneratorApiTest from '../tests/AlphaGeneratorApiTest';

const { Title, Paragraph } = Typography;
const { TabPane } = Tabs;

/**
 * API测试页面
 * 用于集成测试前端组件与后端API的交互
 */
const ApiTestPage: React.FC = () => {
  return (
    <div style={{ padding: 24 }}>
      <Title level={3}>API集成测试</Title>
      <Paragraph>
        此页面用于测试前端组件与后端API的交互。选择相应的测试模块进行测试。
      </Paragraph>
      
      <Card>
        <Tabs defaultActiveKey="alpha">
          <TabPane tab="Alpha因子生成器" key="alpha">
            <AlphaGeneratorApiTest />
          </TabPane>
          {/* 可以添加其他测试模块 */}
        </Tabs>
      </Card>
    </div>
  );
};

export default ApiTestPage;
