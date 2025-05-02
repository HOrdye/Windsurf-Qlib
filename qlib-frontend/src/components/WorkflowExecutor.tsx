import React, { useState } from 'react';
import { Card, Button, Steps, Space, Typography, Radio, Form, Input, Select, Modal, Tooltip, Alert, Divider } from 'antd';
import { 
  PlayCircleOutlined, 
  StopOutlined, 
  CheckCircleOutlined, 
  CloseCircleOutlined,
  InfoCircleOutlined,
  QuestionCircleOutlined,
  LoadingOutlined
} from '@ant-design/icons';
import { useConfigStore } from '../store/configStore';
import { useWorkflowStore } from '../store/workflowStore';
import WorkflowManager, { WorkflowType, WorkflowStatus } from '../services/workflowManager';

const { Title, Text, Paragraph } = Typography;
const { Step } = Steps;
const { Option } = Select;

interface WorkflowExecutorProps {
  onWorkflowStart?: (workflowId: string) => void;
  onWorkflowComplete?: (workflowId: string) => void;
}

const WorkflowExecutor: React.FC<WorkflowExecutorProps> = ({ 
  onWorkflowStart, 
  onWorkflowComplete 
}) => {
  const [form] = Form.useForm();
  const [workflowType, setWorkflowType] = useState<WorkflowType>(WorkflowType.FULL);
  const [configId, setConfigId] = useState<string>('');
  const [executing, setExecuting] = useState<boolean>(false);
  const [showModal, setShowModal] = useState<boolean>(false);
  
  const { templates } = useConfigStore();
  const { addWorkflow, updateWorkflowStatus } = useWorkflowStore();
  
  const workflowManager = WorkflowManager.getInstance();
  
  // 工作流类型选项
  const workflowTypeOptions = [
    { 
      label: '完整工作流', 
      value: WorkflowType.FULL,
      description: '执行完整的数据初始化、模型训练和策略回测流程'
    },
    { 
      label: '训练和回测', 
      value: WorkflowType.TRAIN_BACKTEST,
      description: '跳过数据初始化，直接执行模型训练和策略回测'
    },
    { 
      label: '仅回测', 
      value: WorkflowType.BACKTEST_ONLY,
      description: '使用现有模型，仅执行策略回测'
    }
  ];
  
  // 根据工作流类型获取步骤
  const getWorkflowSteps = (type: WorkflowType) => {
    switch (type) {
      case WorkflowType.FULL:
        return [
          { title: '数据初始化', description: '准备训练和回测所需的数据' },
          { title: '模型训练', description: '训练量化模型' },
          { title: '策略回测', description: '评估策略性能' }
        ];
      case WorkflowType.TRAIN_BACKTEST:
        return [
          { title: '模型训练', description: '训练量化模型' },
          { title: '策略回测', description: '评估策略性能' }
        ];
      case WorkflowType.BACKTEST_ONLY:
        return [
          { title: '策略回测', description: '评估策略性能' }
        ];
      default:
        return [];
    }
  };
  
  // 处理工作流类型变化
  const handleWorkflowTypeChange = (e: any) => {
    setWorkflowType(e.target.value);
  };
  
  // 处理配置选择变化
  const handleConfigChange = (value: string) => {
    setConfigId(value);
  };
  
  // 显示执行确认对话框
  const showExecuteConfirmation = () => {
    form.validateFields()
      .then(() => {
        setShowModal(true);
      })
      .catch(info => {
        console.log('验证失败:', info);
      });
  };
  
  // 执行工作流
  const executeWorkflow = async () => {
    try {
      setExecuting(true);
      setShowModal(false);
      
      const values = await form.validateFields();
      const { workflowName } = values;
      
      // 创建工作流
      const workflowId = workflowManager.createWorkflow(
        workflowName,
        workflowType,
        configId
      );
      
      // 获取创建的工作流并添加到存储
      const workflow = workflowManager.getWorkflow(workflowId);
      if (workflow) {
        addWorkflow(workflow);
        
        // 启动工作流
        const success = await workflowManager.startWorkflow(workflowId);
        
        if (success) {
          if (onWorkflowStart) {
            onWorkflowStart(workflowId);
          }
        } else {
          // 更新工作流状态为失败
          updateWorkflowStatus(workflowId, WorkflowStatus.FAILED);
        }
      }
    } catch (error) {
      console.error('执行工作流失败:', error);
    } finally {
      setExecuting(false);
    }
  };
  
  return (
    <Card title="工作流执行器" style={{ marginBottom: 16 }}>
      <Form
        form={form}
        layout="vertical"
        initialValues={{ workflowName: `工作流_${new Date().toLocaleString()}` }}
      >
        <Form.Item
          name="workflowName"
          label="工作流名称"
          rules={[{ required: true, message: '请输入工作流名称' }]}
        >
          <Input placeholder="请输入工作流名称" />
        </Form.Item>
        
        <Form.Item label="工作流类型">
          <Radio.Group 
            value={workflowType} 
            onChange={handleWorkflowTypeChange}
            optionType="button"
            buttonStyle="solid"
            style={{ width: '100%' }}
          >
            {workflowTypeOptions.map(option => (
              <Tooltip 
                key={option.value} 
                title={option.description}
                placement="bottom"
              >
                <Radio.Button 
                  value={option.value}
                  style={{ width: `${100 / workflowTypeOptions.length}%`, textAlign: 'center' }}
                >
                  {option.label}
                </Radio.Button>
              </Tooltip>
            ))}
          </Radio.Group>
        </Form.Item>
        
        <Form.Item
          label="选择配置"
          required
          validateStatus={configId ? 'success' : 'error'}
          help={!configId && '请选择一个配置'}
        >
          <Select
            placeholder="请选择配置"
            style={{ width: '100%' }}
            onChange={handleConfigChange}
            value={configId || undefined}
          >
            {templates.map(template => (
              <Option key={template.id} value={template.id}>
                {template.name}
              </Option>
            ))}
          </Select>
        </Form.Item>
        
        <Divider />
        
        <Form.Item label="工作流步骤">
          <Steps direction="vertical" size="small" current={-1}>
            {getWorkflowSteps(workflowType).map((step, index) => (
              <Step
                key={index}
                title={step.title}
                description={step.description}
                status="wait"
              />
            ))}
          </Steps>
        </Form.Item>
        
        <Form.Item style={{ marginTop: 24, textAlign: 'right' }}>
          <Button
            type="primary"
            icon={<PlayCircleOutlined />}
            onClick={showExecuteConfirmation}
            disabled={!configId || executing}
            loading={executing}
          >
            执行工作流
          </Button>
        </Form.Item>
      </Form>
      
      <Modal
        title="确认执行工作流"
        open={showModal}
        onOk={executeWorkflow}
        onCancel={() => setShowModal(false)}
        okText="确认执行"
        cancelText="取消"
        okButtonProps={{ icon: <PlayCircleOutlined /> }}
      >
        <Alert
          message="执行工作流将会启动以下步骤"
          description={
            <Steps direction="vertical" size="small" current={-1}>
              {getWorkflowSteps(workflowType).map((step, index) => (
                <Step
                  key={index}
                  title={step.title}
                  description={step.description}
                  status="wait"
                />
              ))}
            </Steps>
          }
          type="info"
          showIcon
        />
        <Paragraph style={{ marginTop: 16 }}>
          <Text strong>配置:</Text> {templates.find(t => t.id === configId)?.name || '未选择配置'}
        </Paragraph>
        <Paragraph>
          <InfoCircleOutlined style={{ marginRight: 8 }} />
          <Text type="secondary">工作流执行后可在任务监控页面查看进度</Text>
        </Paragraph>
      </Modal>
    </Card>
  );
};

export default WorkflowExecutor;
