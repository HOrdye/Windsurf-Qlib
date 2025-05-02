import * as React from 'react';
import { Card, Form, Input, Button, Switch, Select, Divider, message, Tabs, InputNumber, Collapse, Space, Alert } from 'antd';
import { 
  SaveOutlined, 
  ReloadOutlined, 
  LockOutlined,
  DatabaseOutlined,
  ApiOutlined,
  LinkOutlined
} from '@ant-design/icons';

const { TabPane } = Tabs;
const { Panel } = Collapse;
const { Option } = Select;

// 默认设置
const defaultSettings = {
  general: {
    username: '',
    password: '',
    language: 'zh_CN',
    theme: 'light',
    autoSave: true,
    autoSync: false
  },
  server: {
    apiUrl: 'http://127.0.0.1:8080',
    wsUrl: 'ws://127.0.0.1:8080/ws',
    useHttps: false,
    timeout: 30000
  },
  data: {
    defaultProvider: 'local',
    cacheEnabled: true,
    cachePath: '~/.qlib/cache',
    preloadDatasets: ['csi300'],
    autoCleanCache: true,
    cleanCacheInterval: 7
  }
};

// 修改组件类型定义，显式指定返回类型
const Settings = (): JSX.Element => {
  const [form] = Form.useForm();
  const [settings, setSettings] = React.useState(defaultSettings);
  const [loading, setLoading] = React.useState(false);

  // 模拟加载设置
  React.useEffect(() => {
    const savedSettings = localStorage.getItem('qlib_settings');
    if (savedSettings) {
      try {
        const parsedSettings = JSON.parse(savedSettings);
        setSettings(parsedSettings);
        form.setFieldsValue(parsedSettings);
      } catch (e) {
        console.error('解析设置失败:', e);
      }
    }
  }, [form]);

  // 保存设置
  const handleSave = async (values) => {
    setLoading(true);
    
    try {
      // 模拟API请求延迟
      await new Promise(resolve => setTimeout(resolve, 1000));
      
      localStorage.setItem('qlib_settings', JSON.stringify(values));
      setSettings(values);
      message.success('设置已保存');
    } catch (error) {
      message.error('保存设置失败');
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  // 重置设置
  const handleReset = () => {
    form.resetFields();
    form.setFieldsValue(defaultSettings);
  };

  return (
    <div>
      <Card 
        title="系统设置" 
        bordered={false}
        extra={
          <Space>
            <Button 
              icon={<ReloadOutlined />} 
              onClick={handleReset}
            >
              重置
            </Button>
            <Button 
              type="primary" 
              icon={<SaveOutlined />} 
              onClick={() => form.submit()}
              loading={loading}
            >
              保存设置
            </Button>
          </Space>
        }
      >
        <Form
          form={form}
          layout="vertical"
          initialValues={settings}
          onFinish={handleSave}
        >
          <Tabs defaultActiveKey="general">
            <TabPane tab="基本设置" key="general">
              <Alert
                message="轻量级自用配置"
                description="以下设置针对个人开发环境进行了简化，无需复杂的用户管理和权限控制。"
                type="info"
                showIcon
                style={{ marginBottom: 24 }}
              />
              
              <Form.Item
                name={['general', 'username']}
                label="用户名"
              >
                <Input placeholder="用于基本认证" prefix={<LockOutlined />} />
              </Form.Item>
              
              <Form.Item
                name={['general', 'password']}
                label="密码"
              >
                <Input.Password placeholder="留空表示不使用认证" prefix={<LockOutlined />} />
              </Form.Item>
              
              <Form.Item
                name={['general', 'language']}
                label="界面语言"
              >
                <Select>
                  <Option value="zh_CN">简体中文</Option>
                  <Option value="en_US">English</Option>
                </Select>
              </Form.Item>
              
              <Form.Item
                name={['general', 'theme']}
                label="界面主题"
              >
                <Select>
                  <Option value="light">浅色</Option>
                  <Option value="dark">深色</Option>
                </Select>
              </Form.Item>
              
              <Form.Item
                name={['general', 'autoSave']}
                label="自动保存配置"
                valuePropName="checked"
              >
                <Switch />
              </Form.Item>
              
              <Form.Item
                name={['general', 'autoSync']}
                label="自动同步配置到服务器"
                valuePropName="checked"
              >
                <Switch />
              </Form.Item>
            </TabPane>
            
            <TabPane tab="服务器设置" key="server">
              <Form.Item
                name={['server', 'apiUrl']}
                label="Qlib API地址"
              >
                <Input prefix={<ApiOutlined />} placeholder="http://localhost:8080" />
              </Form.Item>
              
              <Form.Item
                name={['server', 'wsUrl']}
                label="WebSocket地址"
              >
                <Input prefix={<LinkOutlined />} placeholder="ws://localhost:8080/ws" />
              </Form.Item>
              
              <Form.Item
                name={['server', 'useHttps']}
                label="启用HTTPS"
                valuePropName="checked"
                tooltip="开发环境可使用自签名证书，生产环境建议启用"
              >
                <Switch />
              </Form.Item>
              
              <Form.Item
                name={['server', 'timeout']}
                label="API超时时间(毫秒)"
              >
                <InputNumber min={1000} max={60000} step={1000} style={{ width: 200 }} />
              </Form.Item>
              
              <Divider />
              
              <Collapse bordered={false}>
                <Panel header="高级服务器设置" key="advanced">
                  <Alert
                    message="注意"
                    description="以下设置仅适用于自定义Qlib服务器部署，如果使用标准配置可忽略。"
                    type="warning"
                    showIcon
                    style={{ marginBottom: 16 }}
                  />
                  
                  <Form.Item
                    label="自定义请求头"
                  >
                    <Input.TextArea 
                      rows={4} 
                      placeholder="格式：key: value (每行一个)"
                    />
                  </Form.Item>
                </Panel>
              </Collapse>
            </TabPane>
            
            <TabPane tab="数据设置" key="data">
              <Form.Item
                name={['data', 'defaultProvider']}
                label="默认数据提供者"
              >
                <Select>
                  <Option value="local">本地文件</Option>
                  <Option value="remote">远程API</Option>
                </Select>
              </Form.Item>
              
              <Form.Item
                name={['data', 'cacheEnabled']}
                label="启用本地缓存"
                valuePropName="checked"
              >
                <Switch />
              </Form.Item>
              
              <Form.Item
                name={['data', 'cachePath']}
                label="缓存路径"
              >
                <Input prefix={<DatabaseOutlined />} />
              </Form.Item>
              
              <Form.Item
                name={['data', 'preloadDatasets']}
                label="预加载数据集"
                tooltip="启动时自动加载到缓存的数据集"
              >
                <Select mode="multiple">
                  <Option value="csi300">CSI300</Option>
                  <Option value="csi500">CSI500</Option>
                  <Option value="csi100">CSI100</Option>
                  <Option value="custom">自定义数据集</Option>
                </Select>
              </Form.Item>
              
              <Form.Item
                name={['data', 'autoCleanCache']}
                label="自动清理缓存"
                valuePropName="checked"
              >
                <Switch />
              </Form.Item>
              
              <Form.Item
                name={['data', 'cleanCacheInterval']}
                label="缓存清理间隔(天)"
              >
                <InputNumber min={1} max={30} style={{ width: 200 }} />
              </Form.Item>
            </TabPane>
          </Tabs>
        </Form>
      </Card>
    </div>
  );
};

export default Settings;
