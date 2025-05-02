import * as React from 'react';
import { List, Card, Tag, Button, Input, Space, Popconfirm, Typography, Empty, Tooltip, Modal } from 'antd';
import { 
  SearchOutlined, 
  EditOutlined, 
  DeleteOutlined, 
  CopyOutlined, 
  StarOutlined, 
  StarFilled,
  HistoryOutlined 
} from '@ant-design/icons';
import { ConfigItem } from '../store/configStore';

const { Title, Text, Paragraph } = Typography;

interface ConfigListProps {
  /**
   * 配置列表
   */
  configs: ConfigItem[];
  /**
   * 加载状态
   */
  loading?: boolean;
  /**
   * 当前选中的配置ID
   */
  selectedId?: string;
  /**
   * 选择配置项回调
   */
  onSelectConfig: (id: string) => void;
  /**
   * 编辑配置回调
   */
  onEditConfig: (id: string) => void;
  /**
   * 删除配置回调
   */
  onDeleteConfig: (id: string) => void;
  /**
   * 复制配置回调
   */
  onDuplicateConfig: (id: string) => void;
  /**
   * 收藏配置回调
   */
  onToggleFavorite: (id: string, favorite: boolean) => void;
  /**
   * 查看历史版本回调
   */
  onViewHistory: (id: string) => void;
}

/**
 * 配置列表组件
 * 展示所有配置文件并提供搜索、编辑等功能
 */
const ConfigList: React.FC<ConfigListProps> = ({
  configs,
  loading = false,
  selectedId,
  onSelectConfig,
  onEditConfig,
  onDeleteConfig,
  onDuplicateConfig,
  onToggleFavorite,
  onViewHistory
}) => {
  const [searchText, setSearchText] = React.useState('');
  const [filterType, setFilterType] = React.useState<'all' | 'favorite'>('all');

  // 过滤配置列表
  const filteredConfigs = configs.filter(config => {
    const matchesSearch = config.name.toLowerCase().includes(searchText.toLowerCase()) || 
                          config.description.toLowerCase().includes(searchText.toLowerCase());
    const matchesFilter = filterType === 'all' || (filterType === 'favorite' && config.favorite);
    
    return matchesSearch && matchesFilter;
  });

  // 获取配置类型标签
  const getConfigTypeTag = (type: string) => {
    const typeColorMap: Record<string, string> = {
      'workflow': 'blue',
      'model': 'green',
      'dataset': 'orange',
      'backtest': 'purple',
      'optimize': 'magenta'
    };
    
    return (
      <Tag color={typeColorMap[type] || 'default'}>
        {type}
      </Tag>
    );
  };

  // 渲染配置项
  const renderConfigItem = (item: ConfigItem) => {
    return (
      <List.Item style={{ padding: 0, marginBottom: 16 }}>
        <Card
          hoverable
          size="small"
          style={{ 
            width: '100%',
            borderLeft: selectedId === item.id ? '3px solid #1890ff' : 'none',
            backgroundColor: selectedId === item.id ? '#e6f7ff' : 'white'
          }}
          onClick={() => onSelectConfig(item.id)}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
            <Space direction="vertical" style={{ width: '100%' }}>
              <div style={{ display: 'flex', alignItems: 'center' }}>
                <Button
                  type="text"
                  size="small"
                  icon={item.favorite ? <StarFilled style={{ color: '#faad14' }} /> : <StarOutlined />}
                  onClick={(e) => {
                    e.stopPropagation();
                    onToggleFavorite(item.id, !item.favorite);
                  }}
                />
                <Title level={5} style={{ margin: 0 }}>
                  {item.name}
                </Title>
                {getConfigTypeTag(item.type)}
                {item.isDefault && (
                  <Tag color="gold">默认</Tag>
                )}
              </div>
              
              <Paragraph 
                ellipsis={{ rows: 2 }}
                style={{ margin: '8px 0', color: '#666' }}
              >
                {item.description || '无描述'}
              </Paragraph>
              
              <div style={{ fontSize: '12px', color: '#999' }}>
                <Space size="small">
                  <span>更新于: {new Date(item.updatedAt).toLocaleString()}</span>
                  <span>•</span>
                  <span>版本: {item.version}</span>
                </Space>
              </div>
            </Space>
            
            <Space>
              <Tooltip title="编辑">
                <Button
                  type="text"
                  size="small"
                  icon={<EditOutlined />}
                  onClick={(e) => {
                    e.stopPropagation();
                    onEditConfig(item.id);
                  }}
                />
              </Tooltip>
              <Tooltip title="复制">
                <Button
                  type="text"
                  size="small"
                  icon={<CopyOutlined />}
                  onClick={(e) => {
                    e.stopPropagation();
                    onDuplicateConfig(item.id);
                  }}
                />
              </Tooltip>
              <Tooltip title="历史版本">
                <Button
                  type="text"
                  size="small"
                  icon={<HistoryOutlined />}
                  onClick={(e) => {
                    e.stopPropagation();
                    onViewHistory(item.id);
                  }}
                />
              </Tooltip>
              <Popconfirm
                title="确定要删除此配置吗?"
                description="此操作无法撤销。"
                okText="确定"
                cancelText="取消"
                onConfirm={(e) => {
                  e?.stopPropagation();
                  onDeleteConfig(item.id);
                }}
              >
                <Tooltip title="删除">
                  <Button
                    type="text"
                    size="small"
                    danger
                    icon={<DeleteOutlined />}
                    onClick={(e) => e.stopPropagation()}
                  />
                </Tooltip>
              </Popconfirm>
            </Space>
          </div>
        </Card>
      </List.Item>
    );
  };

  return (
    <div className="config-list-container">
      <div style={{ marginBottom: 16 }}>
        <Input
          placeholder="搜索配置..."
          prefix={<SearchOutlined />}
          value={searchText}
          onChange={(e) => setSearchText(e.target.value)}
          allowClear
          style={{ marginBottom: 8 }}
        />
        
        <Space>
          <Button
            type={filterType === 'all' ? 'primary' : 'default'}
            onClick={() => setFilterType('all')}
          >
            全部
          </Button>
          <Button
            type={filterType === 'favorite' ? 'primary' : 'default'}
            icon={<StarOutlined />}
            onClick={() => setFilterType('favorite')}
          >
            收藏
          </Button>
        </Space>
      </div>
      
      {filteredConfigs.length > 0 ? (
        <List
          dataSource={filteredConfigs}
          renderItem={renderConfigItem}
          loading={loading}
        />
      ) : (
        <Empty
          image={Empty.PRESENTED_IMAGE_SIMPLE}
          description={
            searchText ? '没有找到匹配的配置' : '暂无配置，请创建新配置'
          }
        />
      )}
    </div>
  );
};

/**
 * 配置历史记录弹窗组件
 */
export const ConfigHistoryModal: React.FC<{
  visible: boolean;
  configId: string | null;
  histories: Array<{id: string, version: string, createdAt: string, comment: string}>;
  onClose: () => void;
  onRestore: (historyId: string) => void;
}> = ({ visible, configId, histories, onClose, onRestore }) => {
  return (
    <Modal
      title="版本历史"
      open={visible}
      footer={null}
      onCancel={onClose}
      width={600}
    >
      {histories.length > 0 ? (
        <List
          dataSource={histories}
          renderItem={(item) => (
            <List.Item
              actions={[
                <Button
                  key="restore"
                  type="link"
                  onClick={() => onRestore(item.id)}
                >
                  恢复此版本
                </Button>
              ]}
            >
              <List.Item.Meta
                title={
                  <Space>
                    <Text strong>版本 {item.version}</Text>
                    <Text type="secondary">
                      {new Date(item.createdAt).toLocaleString()}
                    </Text>
                  </Space>
                }
                description={item.comment || '无备注'}
              />
            </List.Item>
          )}
        />
      ) : (
        <Empty description="暂无历史版本" />
      )}
    </Modal>
  );
};

export default ConfigList;
