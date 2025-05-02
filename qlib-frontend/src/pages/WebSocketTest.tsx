import React, { useState, useEffect, useRef } from 'react';
import { Card, Button, Input, Space, Typography, List, Badge, message } from 'antd';
import WebSocketService, { MessageType, WebSocketState } from '../services/websocket';

const { Text, Title } = Typography;

interface Message {
  type: string;
  payload: any;
  timestamp: number;
}

const WebSocketTest: React.FC = () => {
  const [connected, setConnected] = useState<boolean>(false);
  const [messages, setMessages] = useState<Array<Message>>([]);
  const [messageType, setMessageType] = useState<string>(MessageType.TASK_STATUS);
  const [messagePayload, setMessagePayload] = useState<string>('{"action": "list"}');
  const [wsUrl, setWsUrl] = useState<string>('ws://localhost:8080/ws');
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // 自动滚动到底部
  useEffect(() => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages]);

  // 初始化WebSocket服务
  useEffect(() => {
    try {
      const ws = WebSocketService.getInstance();
      
      // 注册连接状态变化处理器
      const unsubscribeConnection = ws.onConnectionChange((isConnected) => {
        setConnected(isConnected);
        if (isConnected) {
          setMessages(prev => [...prev, {
            type: 'system',
            payload: '连接成功',
            timestamp: Date.now()
          }]);
        } else {
          setMessages(prev => [...prev, {
            type: 'system',
            payload: '连接断开',
            timestamp: Date.now()
          }]);
        }
      });
      
      // 注册消息处理器
      const messageHandlers = Object.values(MessageType).map(type => {
        return ws.on(type as MessageType, (payload) => {
          setMessages(prev => [...prev, {
            type,
            payload,
            timestamp: Date.now()
          }]);
        });
      });
      
      // 清理函数
      return () => {
        unsubscribeConnection();
        messageHandlers.forEach(unsubscribe => unsubscribe());
      };
    } catch (error) {
      console.error('初始化WebSocket服务失败:', error);
      message.error(`初始化WebSocket服务失败: ${error}`);
      return () => {};
    }
  }, []);

  // 连接WebSocket
  const handleConnect = () => {
    try {
      const ws = WebSocketService.getInstance();
      ws.updateConfig({ url: wsUrl });
      ws.connect();
    } catch (error) {
      console.error('连接WebSocket失败:', error);
      message.error(`连接WebSocket失败: ${error}`);
    }
  };

  // 断开WebSocket连接
  const handleDisconnect = () => {
    try {
      const ws = WebSocketService.getInstance();
      ws.disconnect();
    } catch (error) {
      console.error('断开WebSocket连接失败:', error);
      message.error(`断开WebSocket连接失败: ${error}`);
    }
  };

  // 发送消息
  const handleSendMessage = () => {
    try {
      const ws = WebSocketService.getInstance();
      const payload = JSON.parse(messagePayload);
      ws.send(messageType as MessageType, payload);
      
      setMessages(prev => [...prev, {
        type: 'sent',
        payload: { type: messageType, payload },
        timestamp: Date.now()
      }]);
    } catch (error) {
      console.error('发送消息失败:', error);
      message.error(`发送消息失败: ${error}`);
    }
  };

  // 清空消息列表
  const handleClearMessages = () => {
    setMessages([]);
  };
  
  // 获取消息类型的颜色
  const getMessageColor = (type: string) => {
    switch (type) {
      case 'system':
        return '#1890ff';
      case 'sent':
        return '#52c41a';
      case 'error':
        return '#f5222d';
      case MessageType.HEARTBEAT:
        return '#faad14';
      default:
        return '#722ed1';
    }
  };

  // 格式化消息内容
  const formatMessage = (payload: any) => {
    try {
      if (typeof payload === 'object') {
        return JSON.stringify(payload, null, 2);
      }
      return String(payload);
    } catch (error) {
      return `[无法格式化: ${error}]`;
    }
  };

  return (
    <div>
      <Title level={2}>WebSocket 测试</Title>
      
      <Card title="连接设置" style={{ marginBottom: 16 }}>
        <Space direction="vertical" style={{ width: '100%' }}>
          <Input 
            addonBefore="WebSocket URL" 
            value={wsUrl} 
            onChange={(e) => setWsUrl(e.target.value)} 
            placeholder="输入WebSocket服务器地址"
          />
          
          <Space>
            <Button 
              type="primary" 
              onClick={handleConnect} 
              disabled={connected}
            >
              连接
            </Button>
            
            <Button 
              danger 
              onClick={handleDisconnect} 
              disabled={!connected}
            >
              断开连接
            </Button>
            
            <Badge 
              status={connected ? "success" : "error"} 
              text={connected ? "已连接" : "未连接"} 
            />
          </Space>
        </Space>
      </Card>
      
      <Card 
        title="发送消息" 
        style={{ marginBottom: 16 }}
      >
        <Space direction="vertical" style={{ width: '100%' }}>
          <Input 
            addonBefore="消息类型" 
            value={messageType} 
            onChange={(e) => setMessageType(e.target.value)} 
            placeholder="输入消息类型"
          />
          
          <Input.TextArea 
            value={messagePayload} 
            onChange={(e) => setMessagePayload(e.target.value)} 
            placeholder="输入消息内容 (JSON格式)" 
            autoSize={{ minRows: 3, maxRows: 6 }}
          />
          
          <Button 
            type="primary" 
            onClick={handleSendMessage} 
            disabled={!connected}
          >
            发送
          </Button>
        </Space>
      </Card>
      
      <Card 
        title="消息记录" 
        extra={
          <Button onClick={handleClearMessages}>清空</Button>
        }
      >
        <List
          dataSource={messages}
          renderItem={(item) => (
            <List.Item>
              <Space direction="vertical" style={{ width: '100%' }}>
                <div>
                  <Text strong style={{ color: getMessageColor(item.type) }}>
                    [{new Date(item.timestamp).toLocaleTimeString()}] {item.type}
                  </Text>
                </div>
                
                <div style={{ background: '#f5f5f5', padding: 8, borderRadius: 4 }}>
                  <pre style={{ margin: 0, whiteSpace: 'pre-wrap', wordBreak: 'break-all' }}>
                    {formatMessage(item.payload)}
                  </pre>
                </div>
              </Space>
            </List.Item>
          )}
        />
        <div ref={messagesEndRef} />
      </Card>
    </div>
  );
};

export default WebSocketTest;
