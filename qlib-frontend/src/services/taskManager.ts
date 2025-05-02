import WebSocketService, { MessageType, TaskStatus } from './websocket';
import { message } from 'antd';

export interface TaskConfig {
  taskId?: string;
  config: string;  // YAML配置内容
  type: 'train' | 'backtest' | 'optimize';
  name?: string;   // 任务名称
  description?: string; // 任务描述
}

export interface TaskResult {
  taskId: string;
  status: 'success' | 'failed';
  data?: any;
  error?: string;
}

export interface TaskLog {
  taskId: string;
  timestamp: number;
  level: 'info' | 'warning' | 'error';
  message: string;
}

export interface TaskMetrics {
  taskId: string;
  metrics: Record<string, number>;
  timestamp: number;
}

// 任务管理器事件类型
export enum TaskManagerEvent {
  TASK_ADDED = 'task_added',
  TASK_UPDATED = 'task_updated',
  TASK_COMPLETED = 'task_completed',
  TASK_FAILED = 'task_failed',
  TASK_DELETED = 'task_deleted',
  CONNECTION_CHANGED = 'connection_changed',
}

// 任务管理器事件处理器类型
type TaskEventHandler = (taskId: string, data?: any) => void;
type ConnectionEventHandler = (connected: boolean) => void;

class TaskManager {
  private static instance: TaskManager;
  private ws: WebSocketService;
  private activeTasks: Map<string, TaskStatus> = new Map();
  private taskLogs: Map<string, TaskLog[]> = new Map();
  private taskMetrics: Map<string, TaskMetrics> = new Map();
  private eventHandlers: Map<TaskManagerEvent, Function[]> = new Map();
  private isConnected: boolean = false;
  private unsubscribeCallbacks: (() => void)[] = [];

  private constructor() {
    this.ws = WebSocketService.getInstance({
      debug: true, // 开发环境下启用调试日志
    });
    
    this.setupWebSocketHandlers();
    this.connectToServer();
  }

  public static getInstance(): TaskManager {
    if (!TaskManager.instance) {
      TaskManager.instance = new TaskManager();
    }
    return TaskManager.instance;
  }

  // 连接到WebSocket服务器
  private connectToServer(): void {
    try {
      // 监听连接状态变化
      const unsubscribe = this.ws.onConnectionChange(this.handleConnectionChange.bind(this));
      this.unsubscribeCallbacks.push(unsubscribe);
      
      // 连接到服务器
      this.ws.connect();
    } catch (error) {
      console.error('连接到WebSocket服务器失败:', error);
      message.error('无法连接到Qlib服务器');
    }
  }

  // 设置WebSocket事件处理器
  private setupWebSocketHandlers(): void {
    // 处理任务状态更新
    const statusUnsubscribe = this.ws.on(MessageType.TASK_STATUS, (payload: TaskStatus) => {
      this.activeTasks.set(payload.taskId, payload);
      this.notifyTaskUpdate(payload);
      
      // 如果任务完成或失败，触发相应事件
      if (payload.status === 'completed') {
        this.emit(TaskManagerEvent.TASK_COMPLETED, payload.taskId, payload);
      } else if (payload.status === 'failed') {
        this.emit(TaskManagerEvent.TASK_FAILED, payload.taskId, payload);
      } else {
        this.emit(TaskManagerEvent.TASK_UPDATED, payload.taskId, payload);
      }
    });
    
    // 处理任务进度更新
    const progressUnsubscribe = this.ws.on(MessageType.TASK_PROGRESS, (payload: { taskId: string; progress: number }) => {
      const task = this.activeTasks.get(payload.taskId);
      if (task) {
        task.progress = payload.progress;
        this.activeTasks.set(payload.taskId, task);
        this.notifyTaskUpdate(task);
        this.emit(TaskManagerEvent.TASK_UPDATED, payload.taskId, task);
      }
    });
    
    // 处理任务日志
    const logUnsubscribe = this.ws.on(MessageType.TASK_LOG, (payload: TaskLog) => {
      const logs = this.taskLogs.get(payload.taskId) || [];
      logs.push(payload);
      this.taskLogs.set(payload.taskId, logs);
      
      // 如果是错误日志，更新任务状态
      if (payload.level === 'error') {
        const task = this.activeTasks.get(payload.taskId);
        if (task) {
          task.message = payload.message;
          this.activeTasks.set(payload.taskId, task);
          this.notifyTaskUpdate(task);
        }
      }
      
      this.emit(TaskManagerEvent.TASK_UPDATED, payload.taskId, { log: payload });
    });
    
    // 处理任务错误
    const errorUnsubscribe = this.ws.on(MessageType.TASK_ERROR, (payload: { taskId: string; error: string }) => {
      const task = this.activeTasks.get(payload.taskId);
      if (task) {
        task.status = 'failed';
        task.message = payload.error;
        this.activeTasks.set(payload.taskId, task);
        this.notifyTaskUpdate(task);
        this.emit(TaskManagerEvent.TASK_FAILED, payload.taskId, task);
      }
    });
    
    // 处理任务结果
    const resultUnsubscribe = this.ws.on(MessageType.TASK_RESULT, (payload: { taskId: string; result: any }) => {
      const task = this.activeTasks.get(payload.taskId);
      if (task) {
        task.status = 'completed';
        this.activeTasks.set(payload.taskId, task);
        this.notifyTaskUpdate(task);
        this.emit(TaskManagerEvent.TASK_COMPLETED, payload.taskId, {
          ...task,
          result: payload.result
        });
      }
    });
    
    // 保存取消订阅函数
    this.unsubscribeCallbacks.push(
      statusUnsubscribe,
      progressUnsubscribe,
      logUnsubscribe,
      errorUnsubscribe,
      resultUnsubscribe
    );
  }

  // 处理连接状态变化
  private handleConnectionChange(connected: boolean): void {
    const previousState = this.isConnected;
    this.isConnected = connected;
    
    // 只有状态变化时才触发事件
    if (previousState !== connected) {
      this.emit(TaskManagerEvent.CONNECTION_CHANGED, '', connected);
      
      if (connected) {
        message.success('已连接到Qlib服务器');
        // 连接成功后，可以请求活跃任务列表
        this.refreshActiveTasks();
      } else {
        message.warning('与Qlib服务器的连接已断开');
      }
    }
  }

  // 刷新活跃任务列表
  private async refreshActiveTasks(): Promise<void> {
    try {
      const tasks = await this.ws.request(MessageType.TASK_STATUS, { action: 'list' });
      
      // 清空当前任务列表
      this.activeTasks.clear();
      
      // 添加所有活跃任务
      for (const task of tasks) {
        this.activeTasks.set(task.taskId, task);
        this.emit(TaskManagerEvent.TASK_UPDATED, task.taskId, task);
      }
    } catch (error) {
      console.error('获取活跃任务列表失败:', error);
    }
  }

  // 提交新任务
  public async submitTask(taskConfig: TaskConfig): Promise<string> {
    if (!this.isConnected) {
      throw new Error('未连接到Qlib服务器');
    }
    
    try {
      // 生成任务ID
      const taskId = taskConfig.taskId || `task_${Date.now()}`;
      taskConfig.taskId = taskId;
      
      // 初始化任务状态
      const initialStatus: TaskStatus = {
        taskId,
        status: 'pending',
        progress: 0,
        startTime: Date.now(),
      };
      
      this.activeTasks.set(taskId, initialStatus);
      this.emit(TaskManagerEvent.TASK_ADDED, taskId, initialStatus);
      
      // 发送任务到服务器
      await this.ws.request(MessageType.TASK_STATUS, {
        action: 'submit',
        task: taskConfig
      });
      
      return taskId;
    } catch (error) {
      console.error('提交任务失败:', error);
      throw error;
    }
  }

  // 获取任务状态
  public getTaskStatus(taskId: string): TaskStatus | undefined {
    return this.activeTasks.get(taskId);
  }

  // 获取所有任务状态
  public getAllTasks(): TaskStatus[] {
    return Array.from(this.activeTasks.values());
  }

  // 获取任务日志
  public getTaskLogs(taskId: string): TaskLog[] {
    return this.taskLogs.get(taskId) || [];
  }

  // 获取任务指标
  public getTaskMetrics(taskId: string): TaskMetrics | undefined {
    return this.taskMetrics.get(taskId);
  }

  // 取消任务
  public async cancelTask(taskId: string): Promise<boolean> {
    if (!this.isConnected) {
      throw new Error('未连接到Qlib服务器');
    }
    
    try {
      const result = await this.ws.request(MessageType.TASK_STATUS, {
        action: 'cancel',
        taskId
      });
      
      if (result.success) {
        const task = this.activeTasks.get(taskId);
        if (task) {
          task.status = 'failed';
          task.message = '任务已取消';
          this.activeTasks.set(taskId, task);
          this.emit(TaskManagerEvent.TASK_UPDATED, taskId, task);
        }
      }
      
      return result.success;
    } catch (error) {
      console.error('取消任务失败:', error);
      throw error;
    }
  }

  // 删除任务
  public deleteTask(taskId: string): void {
    const task = this.activeTasks.get(taskId);
    if (task) {
      this.activeTasks.delete(taskId);
      this.taskLogs.delete(taskId);
      this.taskMetrics.delete(taskId);
      this.emit(TaskManagerEvent.TASK_DELETED, taskId);
    }
  }

  // 清理已完成的任务
  public cleanupTasks(): void {
    for (const [taskId, status] of this.activeTasks.entries()) {
      if (status.status === 'completed' || status.status === 'failed') {
        this.activeTasks.delete(taskId);
        this.emit(TaskManagerEvent.TASK_DELETED, taskId);
      }
    }
  }

  // 注册事件监听器
  public on(event: TaskManagerEvent.CONNECTION_CHANGED, handler: ConnectionEventHandler): () => void;
  public on(event: Exclude<TaskManagerEvent, TaskManagerEvent.CONNECTION_CHANGED>, handler: TaskEventHandler): () => void;
  public on(event: TaskManagerEvent, handler: Function): () => void {
    if (!this.eventHandlers.has(event)) {
      this.eventHandlers.set(event, []);
    }
    
    this.eventHandlers.get(event)!.push(handler);
    
    // 返回取消订阅函数
    return () => {
      const handlers = this.eventHandlers.get(event);
      if (handlers) {
        const index = handlers.indexOf(handler);
        if (index !== -1) {
          handlers.splice(index, 1);
        }
      }
    };
  }

  // 触发事件
  private emit(event: TaskManagerEvent, taskId: string, data?: any): void {
    const handlers = this.eventHandlers.get(event);
    if (handlers) {
      for (const handler of handlers) {
        try {
          if (event === TaskManagerEvent.CONNECTION_CHANGED) {
            (handler as ConnectionEventHandler)(data as boolean);
          } else {
            (handler as TaskEventHandler)(taskId, data);
          }
        } catch (error) {
          console.error(`执行事件处理器失败 (${event}):`, error);
        }
      }
    }
  }

  // 检查连接状态
  public isServerConnected(): boolean {
    return this.isConnected;
  }

  // 通知任务更新
  private notifyTaskUpdate(status: TaskStatus): void {
    // 这个方法保留用于兼容性，实际上已经通过事件系统替代
    // 未来版本可以移除
  }

  // 销毁实例
  public destroy(): void {
    // 取消所有事件订阅
    for (const unsubscribe of this.unsubscribeCallbacks) {
      unsubscribe();
    }
    this.unsubscribeCallbacks = [];
    
    // 清空事件处理器
    this.eventHandlers.clear();
    
    // 断开WebSocket连接
    this.ws.disconnect();
  }
}

export default TaskManager;
