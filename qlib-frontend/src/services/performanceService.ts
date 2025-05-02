/**
 * 性能优化服务
 * 提供各种性能优化工具和方法
 */

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import CacheService from './cacheService';
import WebSocketService, { MessageType } from './websocket';

// 扩展 Performance 接口，添加 Chrome 特有的 memory 属性
declare global {
  interface Performance {
    memory?: {
      jsHeapSizeLimit: number;
      totalJSHeapSize: number;
      usedJSHeapSize: number;
    };
  }
}

// 防抖函数类型
type DebouncedFunction<T extends (...args: any[]) => any> = {
  (...args: Parameters<T>): void;
  cancel: () => void;
};

// 节流函数类型
type ThrottledFunction<T extends (...args: any[]) => any> = {
  (...args: Parameters<T>): void;
  cancel: () => void;
};

// 缓存键生成器
const generateCacheKey = (prefix: string, args: any[]): string => {
  return `${prefix}:${JSON.stringify(args)}`;
};

/**
 * 防抖函数 - 延迟执行函数，直到停止调用一段时间后才执行
 * @param func 要防抖的函数
 * @param wait 等待时间(毫秒)
 * @param immediate 是否立即执行
 */
export function debounce<T extends (...args: any[]) => any>(
  func: T,
  wait = 300,
  immediate = false
): DebouncedFunction<T> {
  let timeout: number | null = null;
  
  const debounced = function(this: any, ...args: Parameters<T>) {
    const context = this;
    
    const later = function() {
      timeout = null;
      if (!immediate) func.apply(context, args);
    };
    
    const callNow = immediate && !timeout;
    
    if (timeout) {
      clearTimeout(timeout);
    }
    
    timeout = window.setTimeout(later, wait);
    
    if (callNow) func.apply(context, args);
  } as DebouncedFunction<T>;
  
  debounced.cancel = function() {
    if (timeout) {
      clearTimeout(timeout);
      timeout = null;
    }
  };
  
  return debounced;
}

/**
 * 节流函数 - 限制函数在一段时间内只能执行一次
 * @param func 要节流的函数
 * @param wait 等待时间(毫秒)
 * @param options 配置选项
 */
export function throttle<T extends (...args: any[]) => any>(
  func: T,
  wait = 300,
  options = { leading: true, trailing: true }
): ThrottledFunction<T> {
  let timeout: number | null = null;
  let previous = 0;
  let result: any;
  let context: any;
  let args: Parameters<T>;
  
  const later = function() {
    previous = options.leading === false ? 0 : Date.now();
    timeout = null;
    result = func.apply(context, args);
  };
  
  const throttled = function(this: any, ...params: Parameters<T>) {
    const now = Date.now();
    context = this;
    args = params;
    
    if (!previous && options.leading === false) {
      previous = now;
    }
    
    const remaining = wait - (now - previous);
    
    if (remaining <= 0 || remaining > wait) {
      if (timeout) {
        clearTimeout(timeout);
        timeout = null;
      }
      
      previous = now;
      result = func.apply(context, args);
    } else if (!timeout && options.trailing !== false) {
      timeout = window.setTimeout(later, remaining);
    }
    
    return result;
  } as ThrottledFunction<T>;
  
  throttled.cancel = function() {
    if (timeout) {
      clearTimeout(timeout);
      timeout = null;
    }
    previous = 0;
  };
  
  return throttled;
}

/**
 * 使用内存缓存的函数
 * @param func 要缓存的函数
 * @param keyGenerator 缓存键生成器
 * @param ttl 缓存生存时间(毫秒)，默认5分钟
 */
export function memoize<T extends (...args: any[]) => any>(
  func: T,
  keyGenerator: (...args: Parameters<T>) => string = (...args) => JSON.stringify(args),
  ttl = 5 * 60 * 1000
): T {
  const cache = new Map<string, { value: ReturnType<T>, timestamp: number }>();
  
  const memoized = function(this: any, ...args: Parameters<T>): ReturnType<T> {
    const key = keyGenerator.apply(this, args);
    const now = Date.now();
    
    // 检查缓存是否存在且未过期
    const cached = cache.get(key);
    if (cached && now - cached.timestamp < ttl) {
      return cached.value;
    }
    
    // 执行原函数并缓存结果
    const result = func.apply(this, args);
    cache.set(key, { value: result, timestamp: now });
    
    // 清理过期缓存
    for (const [cacheKey, item] of cache.entries()) {
      if (now - item.timestamp > ttl) {
        cache.delete(cacheKey);
      }
    }
    
    return result;
  } as T;
  
  return memoized;
}

/**
 * 使用IndexedDB缓存异步函数结果
 * @param func 要缓存的异步函数
 * @param storeName 存储名称
 * @param keyGenerator 缓存键生成器
 * @param ttl 缓存生存时间(毫秒)，默认1小时
 */
export function cacheAsyncResult<T extends (...args: any[]) => Promise<any>>(
  func: T,
  storeName: string,
  keyGenerator: (...args: Parameters<T>) => string = (...args) => JSON.stringify(args),
  ttl = 60 * 60 * 1000
): (...args: Parameters<T>) => Promise<Awaited<ReturnType<T>>> {
  return async function(this: any, ...args: Parameters<T>): Promise<Awaited<ReturnType<T>>> {
    const key = keyGenerator.apply(this, args);
    
    try {
      // 尝试从缓存获取
      const cached = await CacheService.IndexedDBService.getById(storeName, key) as { data: Awaited<ReturnType<T>>, timestamp: number } | undefined;
      
      // 如果缓存存在且未过期，返回缓存数据
      if (cached && Date.now() - cached.timestamp < ttl) {
        return cached.data;
      }
      
      // 执行原函数
      const result = await func.apply(this, args);
      
      // 缓存结果
      await CacheService.IndexedDBService.save(storeName, {
        id: key,
        data: result,
        timestamp: Date.now()
      });
      
      return result;
    } catch (error) {
      console.error('缓存异步结果失败:', error);
      // 如果缓存操作失败，仍然执行原函数
      return func.apply(this, args);
    }
  };
}

/**
 * 预加载数据的Hook
 * @param fetchFunc 获取数据的函数
 * @param deps 依赖数组
 */
export function usePrefetch<T>(
  fetchFunc: () => Promise<T>,
  deps: React.DependencyList = []
): { data: T | null; loading: boolean; error: Error | null; refetch: () => Promise<void> } {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<Error | null>(null);
  
  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    
    try {
      const result = await fetchFunc();
      setData(result);
    } catch (err) {
      setError(err instanceof Error ? err : new Error(String(err)));
    } finally {
      setLoading(false);
    }
  }, [fetchFunc]);
  
  // 初始加载和依赖变化时重新获取
  useEffect(() => {
    fetchData();
  }, [...deps, fetchData]);
  
  // 提供手动重新获取的方法
  const refetch = useCallback(async () => {
    await fetchData();
  }, [fetchData]);
  
  return { data, loading, error, refetch };
}

/**
 * 虚拟列表Hook
 * @param items 所有项目
 * @param options 配置选项
 */
export function useVirtualList<T>(
  items: T[],
  options: {
    itemHeight: number;
    overscan?: number;
    windowHeight?: number;
  }
): {
  virtualItems: Array<{ index: number; item: T; offsetTop: number }>;
  totalHeight: number;
  scrollTo: (index: number) => void;
  containerRef: React.RefObject<HTMLDivElement>;
} {
  const { itemHeight, overscan = 3, windowHeight = 0 } = options;
  const containerRef = useRef<HTMLDivElement>(null);
  const [scrollTop, setScrollTop] = useState(0);
  
  // 计算可见范围内的项目
  const { virtualItems, totalHeight } = useMemo(() => {
    const height = windowHeight || (containerRef.current?.clientHeight || 0);
    
    // 计算起始和结束索引
    const startIndex = Math.max(0, Math.floor(scrollTop / itemHeight) - overscan);
    const endIndex = Math.min(
      items.length - 1,
      Math.ceil((scrollTop + height) / itemHeight) + overscan
    );
    
    // 生成虚拟项目
    const virtualItems = [];
    for (let i = startIndex; i <= endIndex; i++) {
      virtualItems.push({
        index: i,
        item: items[i],
        offsetTop: i * itemHeight
      });
    }
    
    return {
      virtualItems,
      totalHeight: items.length * itemHeight
    };
  }, [items, itemHeight, scrollTop, overscan, windowHeight]);
  
  // 监听滚动事件
  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;
    
    const handleScroll = () => {
      setScrollTop(container.scrollTop);
    };
    
    container.addEventListener('scroll', handleScroll);
    return () => {
      container.removeEventListener('scroll', handleScroll);
    };
  }, []);
  
  // 滚动到指定索引
  const scrollTo = useCallback((index: number) => {
    if (containerRef.current) {
      containerRef.current.scrollTop = index * itemHeight;
    }
  }, [itemHeight]);
  
  return { virtualItems, totalHeight, scrollTo, containerRef };
}

/**
 * 数据预加载服务
 */
class DataPrefetchService {
  private static instance: DataPrefetchService;
  private prefetchQueue: Map<string, Promise<any>> = new Map();
  private prefetchedData: Map<string, { data: any, timestamp: number }> = new Map();
  private prefetchInProgress: boolean = false;
  private maxConcurrentPrefetch: number = 3;
  private ttl: number = 5 * 60 * 1000; // 默认5分钟
  
  private constructor() {
    // 初始化
    this.startPrefetchProcessor();
  }
  
  public static getInstance(): DataPrefetchService {
    if (!DataPrefetchService.instance) {
      DataPrefetchService.instance = new DataPrefetchService();
    }
    return DataPrefetchService.instance;
  }
  
  /**
   * 添加预加载任务
   * @param key 缓存键
   * @param fetchFunc 获取数据的函数
   * @param priority 优先级(1-10)，数字越大优先级越高
   */
  public addPrefetchTask(key: string, fetchFunc: () => Promise<any>, priority: number = 5): void {
    // 如果已经有数据且未过期，不重复预加载
    const existing = this.prefetchedData.get(key);
    if (existing && Date.now() - existing.timestamp < this.ttl) {
      return;
    }
    
    // 添加到队列
    this.prefetchQueue.set(key, fetchFunc());
    
    // 如果队列过大，移除低优先级任务
    if (this.prefetchQueue.size > 10) {
      const keys = Array.from(this.prefetchQueue.keys());
      // 移除最早添加的任务
      this.prefetchQueue.delete(keys[0]);
    }
  }
  
  /**
   * 获取预加载的数据
   * @param key 缓存键
   */
  public async getPrefetchedData(key: string): Promise<any> {
    // 检查是否已有缓存数据
    const cached = this.prefetchedData.get(key);
    if (cached && Date.now() - cached.timestamp < this.ttl) {
      return cached.data;
    }
    
    // 检查是否在预加载队列中
    const pending = this.prefetchQueue.get(key);
    if (pending) {
      return pending;
    }
    
    return null;
  }
  
  /**
   * 清除预加载的数据
   * @param key 缓存键，如果不提供则清除所有
   */
  public clearPrefetchedData(key?: string): void {
    if (key) {
      this.prefetchedData.delete(key);
      this.prefetchQueue.delete(key);
    } else {
      this.prefetchedData.clear();
      this.prefetchQueue.clear();
    }
  }
  
  /**
   * 启动预加载处理器
   */
  private startPrefetchProcessor(): void {
    setInterval(() => {
      this.processPrefetchQueue();
    }, 1000);
  }
  
  /**
   * 处理预加载队列
   */
  private async processPrefetchQueue(): Promise<void> {
    if (this.prefetchInProgress || this.prefetchQueue.size === 0) {
      return;
    }
    
    this.prefetchInProgress = true;
    
    try {
      // 获取队列中的任务
      const entries = Array.from(this.prefetchQueue.entries());
      const batch = entries.slice(0, this.maxConcurrentPrefetch);
      
      // 并行执行预加载任务
      const results = await Promise.allSettled(
        batch.map(async ([key, promise]) => {
          try {
            const data = await promise;
            return { key, data };
          } catch (error) {
            console.error(`预加载任务失败: ${key}`, error);
            return { key, error };
          }
        })
      );
      
      // 处理结果
      for (const result of results) {
        if (result.status === 'fulfilled') {
          const { key, data, error } = result.value;
          
          // 从队列中移除
          this.prefetchQueue.delete(key);
          
          // 如果成功，保存数据
          if (!error) {
            this.prefetchedData.set(key, {
              data,
              timestamp: Date.now()
            });
          }
        }
      }
      
      // 清理过期数据
      this.cleanupExpiredData();
    } finally {
      this.prefetchInProgress = false;
    }
  }
  
  /**
   * 清理过期数据
   */
  private cleanupExpiredData(): void {
    const now = Date.now();
    for (const [key, item] of this.prefetchedData.entries()) {
      if (now - item.timestamp > this.ttl) {
        this.prefetchedData.delete(key);
      }
    }
  }
}

/**
 * WebSocket性能优化服务
 */
class WebSocketOptimizer {
  private static instance: WebSocketOptimizer;
  private ws: WebSocketService;
  private messageBuffer: Map<MessageType, any[]> = new Map();
  private flushInterval: number = 100; // 刷新间隔(毫秒)
  private flushTimer: number | null = null;
  private subscriptions: Map<string, Set<(data: any) => void>> = new Map();
  
  private constructor() {
    this.ws = WebSocketService.getInstance();
    this.startBuffering();
  }
  
  public static getInstance(): WebSocketOptimizer {
    if (!WebSocketOptimizer.instance) {
      WebSocketOptimizer.instance = new WebSocketOptimizer();
    }
    return WebSocketOptimizer.instance;
  }
  
  /**
   * 发送消息(带批处理)
   * @param type 消息类型
   * @param payload 消息负载
   * @param immediate 是否立即发送
   */
  public send(type: MessageType, payload: any, immediate: boolean = false): void {
    if (immediate) {
      this.ws.send(type, payload);
      return;
    }
    
    // 添加到缓冲区
    if (!this.messageBuffer.has(type)) {
      this.messageBuffer.set(type, []);
    }
    
    this.messageBuffer.get(type)!.push(payload);
    
    // 如果缓冲区过大，立即刷新
    if (this.messageBuffer.get(type)!.length >= 10) {
      this.flushMessageType(type);
    }
  }
  
  /**
   * 订阅消息(带去重)
   * @param type 消息类型
   * @param handler 处理函数
   */
  public subscribe(type: MessageType, handler: (data: any) => void): () => void {
    const key = type.toString();
    
    if (!this.subscriptions.has(key)) {
      this.subscriptions.set(key, new Set());
      
      // 第一个订阅者，注册WebSocket处理器
      this.ws.on(type, (data) => {
        const handlers = this.subscriptions.get(key);
        if (handlers) {
          for (const h of handlers) {
            try {
              h(data);
            } catch (error) {
              console.error(`WebSocket消息处理错误: ${type}`, error);
            }
          }
        }
      });
    }
    
    // 添加到订阅列表
    this.subscriptions.get(key)!.add(handler);
    
    // 返回取消订阅函数
    return () => {
      const handlers = this.subscriptions.get(key);
      if (handlers) {
        handlers.delete(handler);
        
        // 如果没有订阅者，清理资源
        if (handlers.size === 0) {
          this.subscriptions.delete(key);
        }
      }
    };
  }
  
  /**
   * 启动消息缓冲处理
   */
  private startBuffering(): void {
    if (this.flushTimer) {
      clearInterval(this.flushTimer);
    }
    
    this.flushTimer = window.setInterval(() => {
      this.flushAllMessages();
    }, this.flushInterval);
  }
  
  /**
   * 刷新所有缓冲的消息
   */
  private flushAllMessages(): void {
    for (const type of this.messageBuffer.keys()) {
      this.flushMessageType(type);
    }
  }
  
  /**
   * 刷新指定类型的缓冲消息
   * @param type 消息类型
   */
  private flushMessageType(type: MessageType): void {
    const messages = this.messageBuffer.get(type);
    if (!messages || messages.length === 0) {
      return;
    }
    
    // 合并消息
    const batchPayload = {
      batch: true,
      messages: [...messages]
    };
    
    // 发送合并后的消息
    this.ws.send(type, batchPayload);
    
    // 清空缓冲区
    this.messageBuffer.set(type, []);
  }
  
  /**
   * 停止消息缓冲处理
   */
  public stopBuffering(): void {
    if (this.flushTimer) {
      clearInterval(this.flushTimer);
      this.flushTimer = null;
    }
    
    // 刷新所有剩余消息
    this.flushAllMessages();
  }
}

/**
 * 性能监控服务
 */
class PerformanceMonitor {
  private static instance: PerformanceMonitor;
  private metrics: {
    renderTime: number[];
    networkRequests: { url: string, duration: number, timestamp: number }[];
    memoryUsage: { value: number, timestamp: number }[];
    longTasks: { duration: number, timestamp: number }[];
    fps: { value: number, timestamp: number }[];
  };
  private observer: PerformanceObserver | null = null;
  private fpsInterval: number | null = null;
  private lastFrameTime: number = 0;
  private frameCount: number = 0;
  
  private constructor() {
    this.metrics = {
      renderTime: [],
      networkRequests: [],
      memoryUsage: [],
      longTasks: [],
      fps: []
    };
    
    this.setupPerformanceObserver();
    this.startFpsMonitoring();
    this.startMemoryMonitoring();
  }
  
  public static getInstance(): PerformanceMonitor {
    if (!PerformanceMonitor.instance) {
      PerformanceMonitor.instance = new PerformanceMonitor();
    }
    return PerformanceMonitor.instance;
  }
  
  /**
   * 设置性能观察器
   */
  private setupPerformanceObserver(): void {
    if (typeof PerformanceObserver === 'undefined') {
      console.warn('PerformanceObserver API不可用');
      return;
    }
    
    try {
      // 监控长任务
      this.observer = new PerformanceObserver((list) => {
        const entries = list.getEntries();
        
        for (const entry of entries) {
          if (entry.entryType === 'longtask') {
            this.metrics.longTasks.push({
              duration: entry.duration,
              timestamp: Date.now()
            });
          }
        }
      });
      
      this.observer.observe({ entryTypes: ['longtask'] });
      
      // 监控资源加载
      const resourceObserver = new PerformanceObserver((list) => {
        const entries = list.getEntries();
        
        for (const entry of entries) {
          if (entry.entryType === 'resource') {
            const resourceEntry = entry as PerformanceResourceTiming;
            this.metrics.networkRequests.push({
              url: resourceEntry.name,
              duration: resourceEntry.duration,
              timestamp: Date.now()
            });
          }
        }
      });
      
      resourceObserver.observe({ entryTypes: ['resource'] });
    } catch (error) {
      console.error('设置性能观察器失败:', error);
    }
  }
  
  /**
   * 开始FPS监控
   */
  private startFpsMonitoring(): void {
    this.lastFrameTime = performance.now();
    this.frameCount = 0;
    
    const measureFps = () => {
      this.frameCount++;
      const now = performance.now();
      
      // 每秒计算一次FPS
      if (now - this.lastFrameTime >= 1000) {
        const fps = Math.round(this.frameCount * 1000 / (now - this.lastFrameTime));
        
        this.metrics.fps.push({
          value: fps,
          timestamp: Date.now()
        });
        
        // 限制存储的数据量
        if (this.metrics.fps.length > 100) {
          this.metrics.fps.shift();
        }
        
        this.lastFrameTime = now;
        this.frameCount = 0;
      }
      
      requestAnimationFrame(measureFps);
    };
    
    requestAnimationFrame(measureFps);
  }
  
  /**
   * 开始内存监控
   */
  private startMemoryMonitoring(): void {
    const measureMemory = () => {
      if (performance.memory) {
        this.metrics.memoryUsage.push({
          value: performance.memory.usedJSHeapSize,
          timestamp: Date.now()
        });
        
        // 限制存储的数据量
        if (this.metrics.memoryUsage.length > 100) {
          this.metrics.memoryUsage.shift();
        }
      }
    };
    
    // 每10秒测量一次内存使用情况
    setInterval(measureMemory, 10000);
  }
  
  /**
   * 记录组件渲染时间
   * @param componentName 组件名称
   * @param renderTime 渲染时间(毫秒)
   */
  public recordRenderTime(componentName: string, renderTime: number): void {
    this.metrics.renderTime.push(renderTime);
    
    // 限制存储的数据量
    if (this.metrics.renderTime.length > 100) {
      this.metrics.renderTime.shift();
    }
    
    // 如果渲染时间过长，记录警告
    if (renderTime > 16) { // 16ms = 60fps
      console.warn(`组件[${componentName}]渲染时间过长: ${renderTime}ms`);
    }
  }
  
  /**
   * 获取性能指标
   */
  public getMetrics(): typeof this.metrics {
    return { ...this.metrics };
  }
  
  /**
   * 保存性能指标
   */
  public saveMetrics(): void {
    try {
      CacheService.saveUIPreferences({
        ...CacheService.getUIPreferences(),
        performanceMetrics: {
          timestamp: Date.now(),
          averageFps: this.calculateAverageFps(),
          averageRenderTime: this.calculateAverageRenderTime(),
          longTasksCount: this.metrics.longTasks.length,
          memoryTrend: this.calculateMemoryTrend()
        }
      });
    } catch (error) {
      console.error('保存性能指标失败:', error);
    }
  }
  
  /**
   * 计算平均FPS
   */
  private calculateAverageFps(): number {
    if (this.metrics.fps.length === 0) return 0;
    
    const sum = this.metrics.fps.reduce((acc, item) => acc + item.value, 0);
    return Math.round(sum / this.metrics.fps.length);
  }
  
  /**
   * 计算平均渲染时间
   */
  private calculateAverageRenderTime(): number {
    if (this.metrics.renderTime.length === 0) return 0;
    
    const sum = this.metrics.renderTime.reduce((acc, time) => acc + time, 0);
    return sum / this.metrics.renderTime.length;
  }
  
  /**
   * 计算内存使用趋势
   */
  private calculateMemoryTrend(): 'stable' | 'increasing' | 'decreasing' {
    if (this.metrics.memoryUsage.length < 5) return 'stable';
    
    const recent = this.metrics.memoryUsage.slice(-5);
    let increasing = 0;
    let decreasing = 0;
    
    for (let i = 1; i < recent.length; i++) {
      if (recent[i].value > recent[i-1].value) {
        increasing++;
      } else if (recent[i].value < recent[i-1].value) {
        decreasing++;
      }
    }
    
    if (increasing >= 3) return 'increasing';
    if (decreasing >= 3) return 'decreasing';
    return 'stable';
  }
}

/**
 * 使用性能监控的Hook
 * @param componentName 组件名称
 */
export function usePerformanceMonitoring(componentName: string): void {
  const renderTimeRef = useRef<number>(performance.now());
  
  useEffect(() => {
    // 记录渲染开始时间
    renderTimeRef.current = performance.now();
    
    return () => {
      // 组件卸载时记录渲染时间
      const renderTime = performance.now() - renderTimeRef.current;
      PerformanceMonitor.getInstance().recordRenderTime(componentName, renderTime);
    };
  });
}

/**
 * 使用组件渲染计时的Hook
 */
export function useRenderTimer(): { startTimer: () => void; endTimer: () => number } {
  const startTimeRef = useRef<number>(0);
  
  const startTimer = useCallback(() => {
    startTimeRef.current = performance.now();
  }, []);
  
  const endTimer = useCallback(() => {
    const endTime = performance.now();
    const duration = endTime - startTimeRef.current;
    return duration;
  }, []);
  
  return { startTimer, endTimer };
}

// 导出单例实例
export const dataPrefetchService = DataPrefetchService.getInstance();
export const webSocketOptimizer = WebSocketOptimizer.getInstance();
export const performanceMonitor = PerformanceMonitor.getInstance();

// 导出服务类
export {
  DataPrefetchService,
  WebSocketOptimizer,
  PerformanceMonitor
};
