import { v4 as uuidv4 } from 'uuid';
import TaskManager from './taskManager';
import WebSocketService, { MessageType } from './websocket';
import { useTaskStore } from '../store/taskStore';
import { useConfigStore } from '../store/configStore';
import { message } from 'antd';

// 工作流类型
export enum WorkflowType {
  FULL = 'full',           // 完整工作流：数据初始化 -> 模型训练 -> 策略回测
  TRAIN_BACKTEST = 'train_backtest', // 训练和回测：模型训练 -> 策略回测
  BACKTEST_ONLY = 'backtest_only'    // 仅回测：使用现有模型进行回测
}

// 工作流状态
export enum WorkflowStatus {
  PENDING = 'pending',
  RUNNING = 'running',
  COMPLETED = 'completed',
  FAILED = 'failed',
  CANCELED = 'canceled'
}

// 工作流步骤
export interface WorkflowStep {
  id: string;
  name: string;
  type: 'train' | 'backtest' | 'optimize';
  status: 'pending' | 'running' | 'success' | 'failed';
  taskId?: string;
  dependsOn?: string[]; // 依赖的步骤ID
}

// 工作流接口
export interface Workflow {
  id: string;
  name: string;
  type: WorkflowType;
  status: WorkflowStatus;
  steps: WorkflowStep[];
  configId: string;
  startTime: Date;
  endTime?: Date;
  createdBy?: string;
}

/**
 * 工作流管理器
 * 负责创建和管理工作流，协调任务的执行顺序
 */
class WorkflowManager {
  private static instance: WorkflowManager;
  private taskManager: TaskManager;
  private ws: WebSocketService;
  private activeWorkflows: Map<string, Workflow> = new Map();

  private constructor() {
    this.taskManager = TaskManager.getInstance();
    this.ws = WebSocketService.getInstance();
    
    // 监听任务状态变化
    this.ws.on(MessageType.TASK_STATUS, this.handleTaskStatusUpdate.bind(this));
  }

  public static getInstance(): WorkflowManager {
    if (!WorkflowManager.instance) {
      WorkflowManager.instance = new WorkflowManager();
    }
    return WorkflowManager.instance;
  }

  /**
   * 创建新的工作流
   * @param name 工作流名称
   * @param type 工作流类型
   * @param configId 配置ID
   * @returns 创建的工作流ID
   */
  public createWorkflow(name: string, type: WorkflowType, configId: string): string {
    const workflowId = uuidv4();
    const workflow: Workflow = {
      id: workflowId,
      name,
      type,
      status: WorkflowStatus.PENDING,
      steps: this.generateWorkflowSteps(type),
      configId,
      startTime: new Date(),
    };

    this.activeWorkflows.set(workflowId, workflow);
    return workflowId;
  }

  /**
   * 启动工作流
   * @param workflowId 工作流ID
   */
  public async startWorkflow(workflowId: string): Promise<boolean> {
    const workflow = this.activeWorkflows.get(workflowId);
    if (!workflow) {
      message.error('工作流不存在');
      return false;
    }

    // 更新工作流状态
    workflow.status = WorkflowStatus.RUNNING;
    
    try {
      // 获取配置
      const configStore = useConfigStore.getState();
      const config = configStore.getConfigById(workflow.configId);
      
      if (!config) {
        throw new Error('找不到关联的配置');
      }
      
      // 启动第一个没有依赖的步骤
      const initialSteps = workflow.steps.filter(step => 
        !step.dependsOn || step.dependsOn.length === 0
      );
      
      for (const step of initialSteps) {
        await this.startWorkflowStep(workflow, step);
      }
      
      return true;
    } catch (error) {
      console.error('启动工作流失败:', error);
      workflow.status = WorkflowStatus.FAILED;
      message.error(`启动工作流失败: ${error.message}`);
      return false;
    }
  }

  /**
   * 取消工作流
   * @param workflowId 工作流ID
   */
  public async cancelWorkflow(workflowId: string): Promise<boolean> {
    const workflow = this.activeWorkflows.get(workflowId);
    if (!workflow) {
      message.error('工作流不存在');
      return false;
    }

    // 取消所有正在运行的任务
    const runningSteps = workflow.steps.filter(step => step.status === 'running' && step.taskId);
    
    for (const step of runningSteps) {
      if (step.taskId) {
        await this.taskManager.cancelTask(step.taskId);
      }
    }

    // 更新工作流状态
    workflow.status = WorkflowStatus.CANCELED;
    workflow.endTime = new Date();
    
    return true;
  }

  /**
   * 获取工作流
   * @param workflowId 工作流ID
   */
  public getWorkflow(workflowId: string): Workflow | undefined {
    return this.activeWorkflows.get(workflowId);
  }

  /**
   * 获取所有工作流
   */
  public getAllWorkflows(): Workflow[] {
    return Array.from(this.activeWorkflows.values());
  }

  /**
   * 删除工作流
   * @param workflowId 工作流ID
   */
  public deleteWorkflow(workflowId: string): boolean {
    return this.activeWorkflows.delete(workflowId);
  }

  /**
   * 根据工作流类型生成步骤
   * @param type 工作流类型
   */
  private generateWorkflowSteps(type: WorkflowType): WorkflowStep[] {
    const steps: WorkflowStep[] = [];
    
    switch (type) {
      case WorkflowType.FULL:
        // 完整工作流：数据初始化 -> 模型训练 -> 策略回测
        const dataStep: WorkflowStep = {
          id: uuidv4(),
          name: '数据初始化',
          type: 'optimize', // 修改为 'optimize' 类型，与 TaskConfig 中的类型保持一致
          status: 'pending'
        };
        
        const modelStep: WorkflowStep = {
          id: uuidv4(),
          name: '模型训练',
          type: 'train',
          status: 'pending',
          dependsOn: [dataStep.id]
        };
        
        const backtest: WorkflowStep = {
          id: uuidv4(),
          name: '策略回测',
          type: 'backtest',
          status: 'pending',
          dependsOn: [modelStep.id]
        };
        
        steps.push(dataStep, modelStep, backtest);
        break;
        
      case WorkflowType.TRAIN_BACKTEST:
        // 训练和回测：模型训练 -> 策略回测
        const trainStep: WorkflowStep = {
          id: uuidv4(),
          name: '模型训练',
          type: 'train',
          status: 'pending'
        };
        
        const btStep: WorkflowStep = {
          id: uuidv4(),
          name: '策略回测',
          type: 'backtest',
          status: 'pending',
          dependsOn: [trainStep.id]
        };
        
        steps.push(trainStep, btStep);
        break;
        
      case WorkflowType.BACKTEST_ONLY:
        // 仅策略回测
        const backtestOnly: WorkflowStep = {
          id: uuidv4(),
          name: '策略回测',
          type: 'backtest',
          status: 'pending'
        };
        
        steps.push(backtestOnly);
        break;
    }
    
    return steps;
  }

  /**
   * 启动工作流步骤
   * @param workflow 工作流
   * @param step 步骤
   */
  private async startWorkflowStep(workflow: Workflow, step: WorkflowStep): Promise<void> {
    try {
      // 检查依赖是否完成
      if (step.dependsOn && step.dependsOn.length > 0) {
        const dependentSteps = workflow.steps.filter(s => step.dependsOn.includes(s.id));
        const allDependenciesMet = dependentSteps.every(s => s.status === 'success');
        
        if (!allDependenciesMet) {
          return; // 依赖未完成，不启动此步骤
        }
      }
      
      // 更新步骤状态
      step.status = 'running';
      
      // 获取配置
      const configStore = useConfigStore.getState();
      const config = configStore.getConfigById(workflow.configId);
      
      if (!config) {
        throw new Error('找不到关联的配置');
      }
      
      // 创建任务
      const taskId = await this.taskManager.submitTask({
        type: step.type,
        name: step.name,
        config: config.content,
        description: `工作流: ${workflow.name} - 步骤: ${step.name}`
      });
      
      // 更新步骤信息
      step.taskId = taskId;
      
    } catch (error) {
      console.error(`启动工作流步骤 ${step.name} 失败:`, error);
      step.status = 'failed';
      
      // 检查是否需要更新工作流状态
      this.checkWorkflowStatus(workflow);
    }
  }

  /**
   * 处理任务状态更新
   * @param payload 任务状态更新数据
   */
  private handleTaskStatusUpdate(payload: any): void {
    if (!payload || !payload.taskId) return;
    
    // 查找关联的工作流和步骤
    for (const [workflowId, workflow] of this.activeWorkflows.entries()) {
      const step = workflow.steps.find(s => s.taskId === payload.taskId);
      
      if (step) {
        // 更新步骤状态
        if (payload.status === 'completed') {
          step.status = 'success';
          
          // 启动依赖此步骤的下一步
          this.startNextSteps(workflow, step);
        } else if (payload.status === 'failed') {
          step.status = 'failed';
        }
        
        // 检查工作流状态
        this.checkWorkflowStatus(workflow);
        break;
      }
    }
  }

  /**
   * 启动下一步骤
   * @param workflow 工作流
   * @param completedStep 已完成的步骤
   */
  private startNextSteps(workflow: Workflow, completedStep: WorkflowStep): void {
    // 查找依赖此步骤的所有步骤
    const nextSteps = workflow.steps.filter(step => 
      step.dependsOn && step.dependsOn.includes(completedStep.id) && step.status === 'pending'
    );
    
    // 启动符合条件的下一步
    for (const nextStep of nextSteps) {
      this.startWorkflowStep(workflow, nextStep);
    }
  }

  /**
   * 检查工作流状态
   * @param workflow 工作流
   */
  private checkWorkflowStatus(workflow: Workflow): void {
    // 如果有任何步骤失败，则工作流失败
    if (workflow.steps.some(step => step.status === 'failed')) {
      workflow.status = WorkflowStatus.FAILED;
      workflow.endTime = new Date();
      return;
    }
    
    // 如果所有步骤都成功，则工作流完成
    if (workflow.steps.every(step => step.status === 'success')) {
      workflow.status = WorkflowStatus.COMPLETED;
      workflow.endTime = new Date();
      return;
    }
    
    // 其他情况，工作流仍在运行中
    workflow.status = WorkflowStatus.RUNNING;
  }
}

export default WorkflowManager;
