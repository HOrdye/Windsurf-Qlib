import React, { useState, useEffect } from 'react';
import { Form, Input, Button, Card, Typography, message, Space, Divider, Checkbox } from 'antd';
import { UserOutlined, LockOutlined, LoadingOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { useSettingsStore } from '../store/settingsStore';

const { Title, Text } = Typography;

/**
 * 登录页面组件
 */
const Login: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const [rememberMe, setRememberMe] = useState(false);
  const navigate = useNavigate();
  
  const { general, updateGeneralSettings } = useSettingsStore();
  
  // 检查是否已登录
  useEffect(() => {
    // 本地验证逻辑
    const checkAuth = () => {
      const storedUsername = localStorage.getItem('qlib_username');
      if (storedUsername) {
        updateGeneralSettings({ username: storedUsername });
        navigate('/dashboard');
      }
    };
    
    checkAuth();
  }, [navigate, updateGeneralSettings]);
  
  // 处理登录
  const handleLogin = async (values: { username: string; password: string }) => {
    setLoading(true);
    
    try {
      // 这里简化为本地认证，仅匹配设置中的用户名和密码
      if (
        (general.username === '' && general.password === '') || // 首次使用，无需密码
        (values.username === general.username && 
         values.password === general.password)
      ) {
        message.success('登录成功');
        
        // 更新用户名
        updateGeneralSettings({ username: values.username });
        
        // 保存用户名到本地存储（如果开启记住我）
        if (rememberMe) {
          localStorage.setItem('qlib_username', values.username);
        } else {
          localStorage.removeItem('qlib_username');
        }
        
        // 初次登录时设置默认密码
        if (general.password === '') {
          updateGeneralSettings({ password: values.password });
        }
        
        // 重定向到仪表盘
        setTimeout(() => {
          navigate('/dashboard');
        }, 500);
      } else {
        message.error('用户名或密码错误');
      }
    } catch (error) {
      console.error('登录失败:', error);
      message.error('登录失败，请重试');
    } finally {
      setLoading(false);
    }
  };
  
  return (
    <div style={{ 
      display: 'flex', 
      justifyContent: 'center', 
      alignItems: 'center', 
      minHeight: '100vh',
      background: '#f0f2f5'
    }}>
      <Card 
        style={{ 
          width: 400, 
          boxShadow: '0 4px 12px rgba(0, 0, 0, 0.1)',
          borderRadius: '8px'
        }}
        bodyStyle={{ padding: '32px' }}
      >
        <div style={{ textAlign: 'center', marginBottom: 32 }}>
          <Title level={2} style={{ margin: 0, color: '#1890ff' }}>
            Qlib 量化平台
          </Title>
          <Text type="secondary">个人量化交易分析工具</Text>
        </div>
        
        <Form
          name="login"
          initialValues={{ remember: true }}
          onFinish={handleLogin}
          layout="vertical"
        >
          <Form.Item
            name="username"
            rules={[{ required: true, message: '请输入用户名' }]}
          >
            <Input 
              prefix={<UserOutlined />} 
              placeholder="用户名" 
              size="large"
            />
          </Form.Item>
          
          <Form.Item
            name="password"
            rules={[{ required: true, message: '请输入密码' }]}
          >
            <Input.Password 
              prefix={<LockOutlined />} 
              placeholder="密码" 
              size="large"
            />
          </Form.Item>
          
          <Form.Item>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <Checkbox 
                checked={rememberMe}
                onChange={(e) => setRememberMe(e.target.checked)}
              >
                记住我
              </Checkbox>
              {general.username !== '' && (
                <Button type="link" style={{ padding: 0 }}>
                  忘记密码?
                </Button>
              )}
            </div>
          </Form.Item>
          
          <Form.Item>
            <Button 
              type="primary" 
              htmlType="submit" 
              size="large" 
              block 
              loading={loading}
            >
              {loading ? <LoadingOutlined /> : null}
              {general.username === '' ? '创建账户' : '登录'}
            </Button>
          </Form.Item>
          
          {general.username === '' && (
            <div style={{ textAlign: 'center' }}>
              <Text type="secondary">
                首次使用将创建本地账户
              </Text>
            </div>
          )}
        </Form>
        
        <Divider plain>
          <Text type="secondary">安全说明</Text>
        </Divider>
        
        <div style={{ textAlign: 'center' }}>
          <Text type="secondary" style={{ fontSize: '12px' }}>
            用户数据仅存储在本地，不会上传到云端
          </Text>
        </div>
      </Card>
    </div>
  );
};

export default Login;
