import { message } from 'antd';
import config from '../config/environment';
import CacheService from './cacheService';

// 性能优化常量
const BATCH_PROCESSING_INTERVAL = 50; // 消息批处理间隔(毫秒)
const MAX_QUEUE_SIZE = 100; // 最大队列大小
const MESSAGE_CACHE_EXPIRY = 60 * 60 * 1000; // 消息缓存过期时间(1小时)
const PERFORMANCE_METRICS_INTERVAL = 60 * 1000; // 性能指标收集间隔(1分钟)

// WebSocket连接状态
export enum WebSocketState {
  CONNECTING = 0,
  OPEN = 1,
  CLOSING = 2,
  CLOSED = 3,
}

// WebSocket消息类型
export enum MessageType {
  // 系统消息
  HEARTBEAT = 'heartbeat',
  SYSTEM_NOTIFICATION = 'system_notification',
  
  // 任务相关消息
  TASK_STATUS = 'task_status',
  TASK_PROGRESS = 'task_progress',
  TASK_LOG = 'task_log',
  TASK_ERROR = 'task_error',
  TASK_RESULT = 'task_result',
  
  // 配置相关消息
  CONFIG_UPDATE = 'config_update',
  CONFIG_VALIDATE = 'config_validate',
}

// WebSocket消息接口
export interface WebSocketMessage {
  type: MessageType;
  payload: any;
  timestamp: number;
  id?: string; // 消息唯一ID，用于请求-响应模式
}

// 任务状态接口
export interface TaskStatus {
  taskId: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  progress: number;
  message?: string;
  startTime?: number;
  endTime?: number;
}

// 心跳配置
interface HeartbeatConfig {
  enabled: boolean;
  interval: number; // 毫秒
  timeout: number;  // 毫秒
}

// 重连配置
interface ReconnectConfig {
  enabled: boolean;
  maxAttempts: number;
  baseDelay: number; // 毫秒
  maxDelay: number;  // 毫秒
}

// WebSocket服务配置
interface WebSocketConfig {
  url: string;
  protocols?: string | string[];
  heartbeat: HeartbeatConfig;
  reconnect: ReconnectConfig;
  debug: boolean;
  inactivityTimeout: number; // 新增：不活动超时时间（毫秒）
}

// 默认配置
const DEFAULT_CONFIG: WebSocketConfig = {
  url: config.websocket.url,
  heartbeat: {
    enabled: true,
    interval: config.websocket.heartbeatInterval,
    timeout: config.websocket.heartbeatTimeout,
  },
  reconnect: {
    enabled: true,
    maxAttempts: config.websocket.reconnectMaxAttempts,
    baseDelay: config.websocket.reconnectBaseDelay,
    maxDelay: config.websocket.reconnectMaxDelay,
  },
  debug: config.debug,
  inactivityTimeout: config.websocket.inactivityTimeout, // 新增：不活动超时时间（毫秒）
};

class WebSocketService {
  private static instance: WebSocketService;
  private ws: WebSocket | null = null;
  private config: WebSocketConfig;
  private reconnectAttempts = 0;
  private reconnectTimer: number | null = null;
  private heartbeatTimer: number | null = null;
  private heartbeatTimeoutTimer: number | null = null;
  private inactivityTimer: number | null = null;
  private lastActivityTime: number = Date.now();
  private messageHandlers: Map<MessageType, ((payload: any) => void)[]> = new Map();
  private responseHandlers: Map<string, (payload: any) => void> = new Map();
  private connectionHandlers: Array<(connected: boolean) => void> = [];
  private messageQueue: WebSocketMessage[] = [];
  
  // 性能优化相关属性
  private batchProcessingTimer: number | null = null;
  private messageCache: Map<string, { data: any, timestamp: number }> = new Map();
  private pendingMessages: WebSocketMessage[] = [];
  private performanceMetrics = {
    messagesSent: 0,
    messagesReceived: 0,
    reconnections: 0,
    errors: 0,
    averageResponseTime: 0,
    totalResponseTime: 0,
    responseMeasurements: 0
  };
  private metricsTimer: number | null = null;
  private requestTimestamps: Map<string, number> = new Map();

  private constructor(config: Partial<WebSocketConfig> = {}) {
    this.config = { ...DEFAULT_CONFIG, ...config };
    
    // 初始化性能指标收集
    this.startPerformanceMetricsCollection();
  }

  public static getInstance(config?: Partial<WebSocketConfig>): WebSocketService {
    if (!WebSocketService.instance) {
      WebSocketService.instance = new WebSocketService(config);
    } else if (config) {
      // 更新现有实例的配置
      WebSocketService.instance.updateConfig(config);
    }
    return WebSocketService.instance;
  }

  // 更新配置
  public updateConfig(config: Partial<WebSocketConfig>): void {
    const wasConnected = this.isConnected();
    const urlChanged = config.url && config.url !== this.config.url;
    
    this.config = { ...this.config, ...config };
    
    // 如果URL改变且当前已连接，则重新连接
    if (wasConnected && urlChanged) {
      this.disconnect();
      this.connect(this.config.url);
    }
  }

  // 连接到WebSocket服务器
  public connect(url: string = this.config.url): void {
    if (this.ws && this.ws.readyState === WebSocketState.OPEN) {
      this.log('WebSocket已连接');
      return;
    }

    // 清理之前的连接
    this.cleanup();

    try {
      this.log(`正在连接到WebSocket服务器: ${url}`);
      this.ws = new WebSocket(url, this.config.protocols);
      
      this.ws.onopen = this.handleOpen.bind(this);
      this.ws.onmessage = this.handleMessage.bind(this);
      this.ws.onclose = this.handleClose.bind(this);
      this.ws.onerror = this.handleError.bind(this);
    } catch (error) {
      this.logError('WebSocket连接失败:', error);
      this.attemptReconnect();
    }
  }

  // 注册消息处理器
  public on(type: MessageType, handler: (payload: any) => void): () => void {
    if (!this.messageHandlers.has(type)) {
      this.messageHandlers.set(type, []);
    }
    
    const handlers = this.messageHandlers.get(type)!;
    handlers.push(handler);
    
    // 返回取消订阅函数
    return () => this.off(type, handler);
  }

  // 移除消息处理器
  public off(type: MessageType, handler: (payload: any) => void): void {
    if (!this.messageHandlers.has(type)) {
      return;
    }
    
    const handlers = this.messageHandlers.get(type)!;
    const index = handlers.indexOf(handler);
    
    if (index !== -1) {
      handlers.splice(index, 1);
      
      if (handlers.length === 0) {
        this.messageHandlers.delete(type);
      }
    }
  }

  // 注册连接状态变化处理器
  public onConnectionChange(handler: (connected: boolean) => void): () => void {
    this.connectionHandlers.push(handler);
    
    // 如果已连接，立即通知
    if (this.isConnected()) {
      try {
        handler(true);
      } catch (error) {
        this.logError('执行连接状态处理器失败:', error);
      }
    }
    
    // 返回取消订阅函数
    return () => {
      const index = this.connectionHandlers.indexOf(handler);
      if (index !== -1) {
        this.connectionHandlers.splice(index, 1);
      }
    };
  }

  // 发送消息
  public send(type: MessageType, payload: any): void {
    const message: WebSocketMessage = {
      type,
      payload,
      timestamp: Date.now()
    };
    
    this.sendMessage(message);
  }

  // 发送请求并等待响应
  public async request(type: MessageType, payload: any, timeout = 10000): Promise<any> {
    return new Promise((resolve, reject) => {
      const id = `req_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
      const message: WebSocketMessage = {
        type,
        payload,
        timestamp: Date.now(),
        id
      };
      
      // 设置超时处理
      const timeoutId = window.setTimeout(() => {
        this.responseHandlers.delete(id);
        reject(new Error(`请求超时: ${type}`));
      }, timeout);
      
      // 记录请求开始时间（用于性能指标）
      this.requestTimestamps.set(id, Date.now());
      
      // 注册响应处理器
      this.responseHandlers.set(id, (responsePayload) => {
        clearTimeout(timeoutId);
        this.responseHandlers.delete(id);
        
        // 计算响应时间并更新性能指标
        const startTime = this.requestTimestamps.get(id) || 0;
        const responseTime = Date.now() - startTime;
        this.requestTimestamps.delete(id);
        
        this.performanceMetrics.totalResponseTime += responseTime;
        this.performanceMetrics.responseMeasurements++;
        this.performanceMetrics.averageResponseTime = 
          this.performanceMetrics.totalResponseTime / this.performanceMetrics.responseMeasurements;
        
        resolve(responsePayload);
      });
      
      this.sendMessage(message);
    });
  }

  // 关闭连接
  public disconnect(): void {
    if (!this.ws) {
      return;
    }
    
    this.log('关闭WebSocket连接');
    
    // 清理资源
    this.cleanup();
    
    try {
      // 只有在连接打开或正在连接时才需要关闭
      if (this.ws.readyState === WebSocketState.OPEN || this.ws.readyState === WebSocketState.CONNECTING) {
        this.ws.close();
      }
    } catch (error) {
      this.logError('关闭WebSocket连接失败:', error);
    } finally {
      this.ws = null;
    }
  }

  // 检查连接状态
  public isConnected(): boolean {
    return this.ws !== null && this.ws.readyState === WebSocketState.OPEN;
  }

  // 获取当前连接状态
  public getState(): WebSocketState | null {
    return this.ws ? this.ws.readyState : null;
  }

  // 清空消息队列
  public clearMessageQueue(): void {
    this.messageQueue = [];
  }

  // 处理WebSocket打开事件
  private handleOpen(event: Event): void {
    this.log('WebSocket连接已打开');
    
    // 重置重连尝试次数
    this.reconnectAttempts = 0;
    
    // 启动心跳检测
    this.startHeartbeat();
    
    // 启动不活动计时器
    this.startInactivityTimer();
    
    // 通知连接状态变化
    this.notifyConnectionChange(true);
    
    // 处理离线消息队列
    this.processMessageQueue();
    
    // 启动批处理定时器
    this.startBatchProcessing();
  }

  // 处理WebSocket消息事件
  private handleMessage(event: MessageEvent): void {
    try {
      const data = JSON.parse(event.data) as WebSocketMessage;
      this.log(`收到消息: ${data.type}`);
      
      // 更新性能指标
      this.performanceMetrics.messagesReceived++;
      
      // 更新最后活动时间
      this.lastActivityTime = Date.now();
      
      // 重置不活动计时器
      this.resetInactivityTimer();
      
      // 处理心跳响应
      if (data.type === MessageType.HEARTBEAT) {
        this.handleHeartbeatResponse();
        return;
      }
      
      // 处理响应消息
      if (data.id && this.responseHandlers.has(data.id)) {
        const handler = this.responseHandlers.get(data.id)!;
        handler(data.payload);
        return;
      }
      
      // 缓存消息（用于重复请求优化）
      const cacheKey = `${data.type}_${JSON.stringify(data.payload)}`;
      this.messageCache.set(cacheKey, {
        data: data.payload,
        timestamp: Date.now()
      });
      
      // 处理普通消息
      if (this.messageHandlers.has(data.type)) {
        const handlers = this.messageHandlers.get(data.type)!;
        for (const handler of handlers) {
          try {
            handler(data.payload);
          } catch (error) {
            this.logError(`执行消息处理器失败: ${data.type}`, error);
          }
        }
      }
    } catch (error) {
      this.logError('处理WebSocket消息失败:', error);
    }
  }

  // 处理WebSocket关闭事件
  private handleClose(event: CloseEvent): void {
    this.log(`WebSocket连接已关闭: ${event.code} ${event.reason}`);
    
    // 清理资源
    this.cleanup();
    
    // 通知连接状态变化
    this.notifyConnectionChange(false);
    
    // 尝试重新连接
    this.attemptReconnect();
  }

  // 处理WebSocket错误事件
  private handleError(event: Event): void {
    this.logError('WebSocket错误:', event);
    this.performanceMetrics.errors++;
  }

  // 发送消息
  private sendMessage(message: WebSocketMessage): void {
    // 检查缓存中是否有相同的请求（避免重复请求）
    if (!message.id && message.type !== MessageType.HEARTBEAT) {
      const cacheKey = `${message.type}_${JSON.stringify(message.payload)}`;
      const cachedItem = this.messageCache.get(cacheKey);
      
      if (cachedItem && (Date.now() - cachedItem.timestamp < MESSAGE_CACHE_EXPIRY)) {
        this.log(`使用缓存的响应: ${message.type}`);
        return;
      }
    }
    
    // 如果连接已打开，直接发送
    if (this.isConnected()) {
      try {
        this.ws!.send(JSON.stringify(message));
        this.performanceMetrics.messagesSent++;
        this.log(`已发送消息: ${message.type}`);
      } catch (error) {
        this.logError('发送消息失败:', error);
        this.messageQueue.push(message);
        
        // 限制队列大小
        if (this.messageQueue.length > MAX_QUEUE_SIZE) {
          this.messageQueue.shift();
        }
      }
    } else {
      // 如果连接未打开，加入队列
      this.messageQueue.push(message);
      
      // 限制队列大小
      if (this.messageQueue.length > MAX_QUEUE_SIZE) {
        this.messageQueue.shift();
      }
      
      // 如果未连接，尝试连接
      if (!this.ws || this.ws.readyState === WebSocketState.CLOSED) {
        this.connect();
      }
    }
  }

  // 处理离线消息队列
  private processMessageQueue(): void {
    if (this.messageQueue.length === 0 || !this.isConnected()) {
      return;
    }
    
    this.log(`处理离线消息队列: ${this.messageQueue.length}条消息`);
    
    // 复制队列并清空原队列
    const queue = [...this.messageQueue];
    this.messageQueue = [];
    
    // 发送队列中的消息
    for (const message of queue) {
      try {
        this.ws!.send(JSON.stringify(message));
        this.performanceMetrics.messagesSent++;
      } catch (error) {
        this.logError('发送队列消息失败:', error);
        this.messageQueue.push(message);
      }
    }
  }

  // 启动批处理
  private startBatchProcessing(): void {
    if (this.batchProcessingTimer) {
      clearInterval(this.batchProcessingTimer);
    }
    
    this.batchProcessingTimer = window.setInterval(() => {
      if (this.pendingMessages.length === 0 || !this.isConnected()) {
        return;
      }
      
      // 批量发送消息
      const batch = [...this.pendingMessages];
      this.pendingMessages = [];
      
      try {
        const batchMessage = {
          type: 'batch',
          payload: batch,
          timestamp: Date.now()
        };
        
        this.ws!.send(JSON.stringify(batchMessage));
        this.performanceMetrics.messagesSent++;
      } catch (error) {
        this.logError('批量发送消息失败:', error);
        // 失败时，将消息放回队列
        this.pendingMessages.push(...batch);
      }
    }, BATCH_PROCESSING_INTERVAL);
  }

  // 尝试重新连接
  private attemptReconnect(): void {
    if (!this.config.reconnect.enabled) {
      return;
    }
    
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    
    if (this.reconnectAttempts >= this.config.reconnect.maxAttempts) {
      this.log(`重连次数超过最大限制 (${this.config.reconnect.maxAttempts})`);
      message.error('无法连接到Qlib服务器，请检查服务器状态');
      return;
    }
    
    this.reconnectAttempts++;
    this.performanceMetrics.reconnections++;
    
    // 使用指数退避算法计算延迟
    const delay = Math.min(
      this.config.reconnect.baseDelay * Math.pow(1.5, this.reconnectAttempts - 1),
      this.config.reconnect.maxDelay
    );
    
    this.log(`尝试重新连接 (${this.reconnectAttempts}/${this.config.reconnect.maxAttempts}) 在 ${delay}ms 后`);
    
    this.reconnectTimer = window.setTimeout(() => {
      this.reconnectTimer = null;
      this.connect();
    }, delay);
  }

  // 启动心跳检测
  private startHeartbeat(): void {
    if (!this.config.heartbeat.enabled) {
      return;
    }
    
    this.stopHeartbeat();
    
    this.heartbeatTimer = window.setInterval(() => {
      if (this.isConnected()) {
        this.sendHeartbeat();
      } else {
        this.stopHeartbeat();
      }
    }, this.config.heartbeat.interval);
  }

  // 停止心跳检测
  private stopHeartbeat(): void {
    if (this.heartbeatTimer) {
      clearInterval(this.heartbeatTimer);
      this.heartbeatTimer = null;
    }
    
    if (this.heartbeatTimeoutTimer) {
      clearTimeout(this.heartbeatTimeoutTimer);
      this.heartbeatTimeoutTimer = null;
    }
  }

  // 发送心跳消息
  private sendHeartbeat(): void {
    this.send(MessageType.HEARTBEAT, { timestamp: Date.now() });
    
    // 设置心跳超时
    if (this.heartbeatTimeoutTimer) {
      clearTimeout(this.heartbeatTimeoutTimer);
    }
    
    this.heartbeatTimeoutTimer = window.setTimeout(() => {
      this.log('心跳超时，重新连接');
      this.disconnect();
      this.connect();
    }, this.config.heartbeat.timeout);
  }

  // 处理心跳响应
  private handleHeartbeatResponse(): void {
    if (this.heartbeatTimeoutTimer) {
      clearTimeout(this.heartbeatTimeoutTimer);
      this.heartbeatTimeoutTimer = null;
    }
  }

  // 清理资源
  private cleanup(): void {
    this.stopHeartbeat();
    
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    
    if (this.inactivityTimer) {
      clearTimeout(this.inactivityTimer);
      this.inactivityTimer = null;
    }
    
    if (this.batchProcessingTimer) {
      clearInterval(this.batchProcessingTimer);
      this.batchProcessingTimer = null;
    }
  }

  // 通知连接状态变化
  private notifyConnectionChange(connected: boolean): void {
    for (const handler of this.connectionHandlers) {
      try {
        handler(connected);
      } catch (error) {
        this.logError('执行连接状态处理器失败:', error);
      }
    }
  }

  // 启动不活动计时器
  private startInactivityTimer(): void {
    if (this.inactivityTimer) {
      clearTimeout(this.inactivityTimer);
    }
    
    this.inactivityTimer = window.setTimeout(() => {
      this.log('长时间未活动，关闭连接');
      this.disconnect();
    }, this.config.inactivityTimeout);
  }

  // 重置不活动计时器
  private resetInactivityTimer(): void {
    if (this.inactivityTimer) {
      clearTimeout(this.inactivityTimer);
    }
    
    this.inactivityTimer = window.setTimeout(() => {
      this.log('长时间未活动，关闭连接');
      this.disconnect();
    }, this.config.inactivityTimeout);
  }

  // 启动性能指标收集
  private startPerformanceMetricsCollection(): void {
    if (this.metricsTimer) {
      clearInterval(this.metricsTimer);
    }
    
    this.metricsTimer = window.setInterval(() => {
      // 清理过期的消息缓存
      this.cleanupMessageCache();
      
      // 保存性能指标到缓存
      this.savePerformanceMetrics();
      
      // 如果开启了调试模式，输出性能指标
      if (this.config.debug) {
        console.log('[WebSocket性能指标]', this.performanceMetrics);
      }
    }, PERFORMANCE_METRICS_INTERVAL);
  }

  // 清理过期的消息缓存
  private cleanupMessageCache(): void {
    const now = Date.now();
    for (const [key, item] of this.messageCache.entries()) {
      if (now - item.timestamp > MESSAGE_CACHE_EXPIRY) {
        this.messageCache.delete(key);
      }
    }
  }

  // 保存性能指标
  private savePerformanceMetrics(): void {
    try {
      // 使用缓存服务保存性能指标
      const metrics = {
        ...this.performanceMetrics,
        timestamp: Date.now(),
        cacheSize: this.messageCache.size,
        queueSize: this.messageQueue.length
      };
      
      // 保存到LocalStorage
      CacheService.saveUIPreferences({
        ...CacheService.getUIPreferences(),
        websocketMetrics: metrics
      });
    } catch (error) {
      this.logError('保存性能指标失败:', error);
    }
  }

  // 日志输出
  private log(message: string): void {
    if (this.config.debug) {
      console.log(`[WebSocket] ${message}`);
    }
  }

  // 错误日志输出
  private logError(message: string, error: any): void {
    console.error(`[WebSocket] ${message}`, error);
  }
}

export default WebSocketService;
