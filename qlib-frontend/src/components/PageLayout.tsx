import * as React from 'react';
import { 
  Layout, Menu, Button, Dropdown, Avatar, 
  Typography, Badge, theme, Drawer, Tooltip,
  Space
} from 'antd';
import { 
  MenuFoldOutlined, 
  MenuUnfoldOutlined,
  DashboardOutlined,
  FileTextOutlined,
  RocketOutlined,
  LineChartOutlined,
  SettingOutlined,
  BellOutlined,
  GithubOutlined,
  UserOutlined,
  LogoutOutlined,
  BugOutlined,
  QuestionCircleOutlined,
  BulbOutlined
} from '@ant-design/icons';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { useSettingsStore } from '../store/settingsStore';

const { Header, Sider, Content } = Layout;
const { Title, Text } = Typography;
const { useToken } = theme;

interface PageLayoutProps {
  children: React.ReactNode;
  title?: string;
}

/**
 * 页面布局组件
 * 提供全局导航和内容区域
 */
const PageLayout = ({ 
  children, 
  title = 'Qlib 量化平台' 
}: PageLayoutProps) => {
  const [collapsed, setCollapsed] = React.useState(false);
  const [notifications, setNotifications] = React.useState<number>(0);
  const [notificationDrawerOpen, setNotificationDrawerOpen] = React.useState(false);
  const [mobileView, setMobileView] = React.useState(false);
  
  const location = useLocation();
  const navigate = useNavigate();
  const { token } = useToken();
  
  const { general, resetSettings } = useSettingsStore();
  
  // 处理屏幕尺寸变化
  React.useEffect(() => {
    const handleResize = () => {
      setMobileView(window.innerWidth < 768);
      if (window.innerWidth < 768 && !collapsed) {
        setCollapsed(true);
      }
    };
    
    window.addEventListener('resize', handleResize);
    handleResize(); // 初始化时检查
    
    return () => window.removeEventListener('resize', handleResize);
  }, [collapsed]);
  
  // 获取当前选中的菜单项
  const getSelectedKey = () => {
    const path = location.pathname;
    if (path.startsWith('/dashboard')) return ['dashboard'];
    if (path.startsWith('/config')) return ['config'];
    if (path.startsWith('/task')) return ['task'];
    if (path.startsWith('/visualization')) return ['visualization'];
    if (path.startsWith('/settings')) return ['settings'];
    return ['dashboard'];
  };
  
  // 菜单项
  const menuItems = [
    {
      key: 'dashboard',
      icon: <DashboardOutlined />,
      label: '仪表盘',
      onClick: () => navigate('/dashboard')
    },
    {
      key: 'config',
      icon: <FileTextOutlined />,
      label: '配置管理',
      onClick: () => navigate('/config')
    },
    {
      key: 'task',
      icon: <RocketOutlined />,
      label: '任务监控',
      onClick: () => navigate('/task')
    },
    {
      key: 'visualization',
      icon: <LineChartOutlined />,
      label: '数据可视化',
      onClick: () => navigate('/visualization')
    },
    {
      key: 'settings',
      icon: <SettingOutlined />,
      label: '系统设置',
      onClick: () => navigate('/settings')
    }
  ];
  
  // 用户下拉菜单
  const userMenu = {
    items: [
      {
        key: 'profile',
        icon: <UserOutlined />,
        label: '个人信息'
      },
      {
        key: 'help',
        icon: <QuestionCircleOutlined />,
        label: '使用帮助'
      },
      {
        key: 'report',
        icon: <BugOutlined />,
        label: '问题反馈'
      },
      {
        type: 'divider'
      },
      {
        key: 'logout',
        icon: <LogoutOutlined />,
        label: '退出登录',
        danger: true
      }
    ]
  };
  
  // 通知列表（模拟数据）
  const notificationItems = [
    {
      id: '1',
      title: '任务完成',
      content: '模型训练任务 "LGBM_基础模型" 已完成',
      time: '10分钟前',
      read: false
    },
    {
      id: '2',
      title: '系统提醒',
      content: 'Qlib 已更新到最新版本 v0.9.0',
      time: '1小时前',
      read: true
    },
    {
      id: '3',
      title: '任务失败',
      content: '回测任务 "Alpha158_回测" 执行失败',
      time: '3小时前',
      read: false
    }
  ];
  
  // 初始化通知数量
  React.useEffect(() => {
    const unreadCount = notificationItems.filter(item => !item.read).length;
    setNotifications(unreadCount);
  }, []);
  
  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Sider 
        trigger={null} 
        collapsible 
        collapsed={collapsed}
        theme="light"
        style={{
          overflow: 'auto',
          height: '100vh',
          position: 'fixed',
          left: 0,
          top: 0,
          bottom: 0,
          boxShadow: token.boxShadow,
          zIndex: 999
        }}
        width={220}
      >
        <div style={{ 
          height: 64, 
          display: 'flex', 
          alignItems: 'center', 
          justifyContent: collapsed ? 'center' : 'flex-start',
          padding: collapsed ? 0 : '0 16px',
          overflow: 'hidden'
        }}>
          {collapsed ? (
            <Avatar 
              shape="square" 
              size={32} 
              style={{ backgroundColor: token.colorPrimary }}
            >
              Q
            </Avatar>
          ) : (
            <Title 
              level={4}
              style={{ 
                margin: 0, 
                color: token.colorPrimary,
                whiteSpace: 'nowrap',
                overflow: 'hidden',
                textOverflow: 'ellipsis'
              }}
            >
              Qlib 量化平台
            </Title>
          )}
        </div>
        
        <Menu
          mode="inline"
          selectedKeys={getSelectedKey()}
          style={{ borderRight: 0 }}
          items={menuItems}
        />
        
        {!collapsed && (
          <div style={{ 
            position: 'absolute', 
            bottom: 0, 
            width: '100%', 
            padding: '16px',
            borderTop: `1px solid ${token.colorBorderSecondary}`
          }}>
            <Button
              type="default"
              icon={<GithubOutlined />}
              style={{ width: '100%' }}
              onClick={() => window.open('https://github.com/microsoft/qlib', '_blank')}
            >
              Qlib 文档
            </Button>
          </div>
        )}
      </Sider>
      
      <Layout style={{ marginLeft: collapsed ? 80 : 220, transition: 'all 0.2s' }}>
        <Header style={{ 
          padding: '0 16px', 
          background: token.colorBgContainer,
          display: 'flex',
          alignItems: 'center',
          boxShadow: token.boxShadowTertiary,
          position: 'sticky',
          top: 0,
          zIndex: 2,
          width: '100%',
          height: 64
        }}>
          <Button
            type="text"
            icon={collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
            onClick={() => setCollapsed(!collapsed)}
            style={{ fontSize: '16px', width: 40, height: 40 }}
          />
          
          <Title 
            level={4} 
            style={{ 
              margin: 0, 
              flex: 1, 
              color: token.colorTextHeading,
              overflow: 'hidden',
              textOverflow: 'ellipsis',
              whiteSpace: 'nowrap',
              padding: '0 16px'
            }}
          >
            {title}
          </Title>
          
          <div style={{ display: 'flex', alignItems: 'center' }}>
            <Tooltip title={general.theme === 'light' ? '切换至深色模式' : '切换至浅色模式'}>
              <Button
                type="text"
                icon={general.theme === 'light' ? <BulbOutlined /> : <BulbOutlined />}
                style={{ marginRight: 8 }}
                onClick={() => {
                  useSettingsStore.getState().updateGeneralSettings({
                    theme: general.theme === 'light' ? 'dark' : 'light'
                  });
                }}
              />
            </Tooltip>
            
            <Badge count={notifications} size="small">
              <Button
                type="text"
                icon={<BellOutlined />}
                style={{ marginRight: 8 }}
                onClick={() => setNotificationDrawerOpen(true)}
              />
            </Badge>
            
            <Dropdown menu={userMenu} trigger={['click']}>
              <Button type="text" style={{ height: 40 }}>
                <Space>
                  <Avatar 
                    size="small" 
                    icon={<UserOutlined />} 
                    style={{ backgroundColor: token.colorPrimary }}
                  />
                  {!mobileView && (
                    <Text>{general.username || '用户'}</Text>
                  )}
                </Space>
              </Button>
            </Dropdown>
          </div>
        </Header>
        
        <Content style={{ margin: '16px', overflow: 'initial', minHeight: 'calc(100vh - 64px - 32px)' }}>
          {children}
        </Content>
      </Layout>
      
      <Drawer
        title="通知中心"
        placement="right"
        open={notificationDrawerOpen}
        onClose={() => setNotificationDrawerOpen(false)}
        width={320}
      >
        {notificationItems.length > 0 ? (
          <div>
            {notificationItems.map(item => (
              <div 
                key={item.id} 
                style={{ 
                  padding: '12px',
                  borderBottom: `1px solid ${token.colorBorderSecondary}`,
                  backgroundColor: item.read ? 'transparent' : token.colorBgTextHover,
                  borderRadius: token.borderRadius
                }}
              >
                <div style={{ 
                  display: 'flex', 
                  justifyContent: 'space-between', 
                  marginBottom: 4 
                }}>
                  <Text strong>{item.title}</Text>
                  <Text type="secondary" style={{ fontSize: 12 }}>{item.time}</Text>
                </div>
                <Text>{item.content}</Text>
              </div>
            ))}
          </div>
        ) : (
          <div style={{ textAlign: 'center', padding: '40px 0' }}>
            <Text type="secondary">暂无通知</Text>
          </div>
        )}
      </Drawer>
    </Layout>
  );
};

export default PageLayout;
