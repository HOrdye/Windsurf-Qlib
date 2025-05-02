/**
 * 性能优化高阶组件
 * 自动为组件应用性能优化，包括记忆化、渲染追踪等
 */

import React, { memo, useEffect, useRef } from 'react';
import { performanceMonitor } from '../services/performanceService';

interface WithPerformanceOptimizationOptions {
  // 组件名称，用于性能日志
  componentName?: string;
  // 是否启用渲染时间追踪
  trackRenderTime?: boolean;
  // 是否启用深度比较
  deepCompare?: boolean;
  // 是否记录到控制台
  logToConsole?: boolean;
}

/**
 * 性能优化高阶组件
 * @param Component 要优化的组件
 * @param options 优化选项
 */
export function withPerformanceOptimization<P = any>(
  Component: any, // 使用 any 类型避免 React 18 类型兼容性问题
  options: WithPerformanceOptimizationOptions = {}
) {
  const {
    componentName = Component.displayName || Component.name || 'UnknownComponent',
    trackRenderTime = true,
    deepCompare = false,
    logToConsole = false
  } = options;

  // 创建优化后的组件
  const OptimizedComponent = (props: P) => {
    const renderStartTimeRef = useRef<number>(0);
    
    // 记录渲染开始时间
    useEffect(() => {
      if (trackRenderTime) {
        renderStartTimeRef.current = performance.now();
        
        // 在组件卸载时记录渲染时间
        return () => {
          const renderTime = performance.now() - renderStartTimeRef.current;
          
          // 确保在测试环境中也能正确执行
          try {
            performanceMonitor.recordRenderTime(componentName, renderTime);
            
            if (logToConsole) {
              console.log(`[性能] ${componentName} 渲染时间: ${renderTime.toFixed(2)}ms`);
            }
          } catch (error) {
            console.error(`[性能监控错误] ${componentName}:`, error);
          }
        };
      }
      return undefined;
    });
    
    return <Component {...props} />;
  };
  
  // 设置显示名称
  OptimizedComponent.displayName = `WithPerformanceOptimization(${componentName})`;
  
  // 复制原组件的静态属性
  if (Component.defaultProps) {
    OptimizedComponent.defaultProps = { ...Component.defaultProps };
  }
  
  // 使用React.memo进行记忆化
  // @ts-ignore - 忽略类型错误，因为 memo 的类型定义在 React 18 中有变化
  return memo(OptimizedComponent, deepCompare ? (prevProps, nextProps) => {
    // 深度比较所有属性
    return JSON.stringify(prevProps) === JSON.stringify(nextProps);
  } : undefined);
}

/**
 * 使用性能优化的类组件装饰器
 * @param options 优化选项
 */
export function PerformanceOptimized(options: WithPerformanceOptimizationOptions = {}) {
  return function(Component: any): any {
    const {
      componentName = Component.displayName || Component.name || 'UnknownComponent',
      trackRenderTime = true,
      logToConsole = false
    } = options;
    
    // 保存原始的生命周期方法
    const originalComponentDidMount = Component.prototype.componentDidMount;
    const originalComponentDidUpdate = Component.prototype.componentDidUpdate;
    const originalComponentWillUnmount = Component.prototype.componentWillUnmount;
    
    // 增强componentDidMount
    Component.prototype.componentDidMount = function() {
      if (trackRenderTime) {
        this.__renderStartTime = performance.now();
      }
      
      if (originalComponentDidMount) {
        originalComponentDidMount.apply(this);
      }
    };
    
    // 增强componentDidUpdate
    Component.prototype.componentDidUpdate = function() {
      if (trackRenderTime) {
        const renderTime = performance.now() - this.__renderStartTime;
        try {
          performanceMonitor.recordRenderTime(componentName, renderTime);
          
          if (logToConsole) {
            console.log(`[性能] ${componentName} 更新时间: ${renderTime.toFixed(2)}ms`);
          }
        } catch (error) {
          console.error(`[性能监控错误] ${componentName}:`, error);
        }
        
        this.__renderStartTime = performance.now();
      }
      
      if (originalComponentDidUpdate) {
        originalComponentDidUpdate.apply(this, arguments);
      }
    };
    
    // 增强componentWillUnmount
    Component.prototype.componentWillUnmount = function() {
      if (trackRenderTime && this.__renderStartTime) {
        const renderTime = performance.now() - this.__renderStartTime;
        try {
          performanceMonitor.recordRenderTime(componentName, renderTime);
          
          if (logToConsole) {
            console.log(`[性能] ${componentName} 最终渲染时间: ${renderTime.toFixed(2)}ms`);
          }
        } catch (error) {
          console.error(`[性能监控错误] ${componentName}:`, error);
        }
      }
      
      if (originalComponentWillUnmount) {
        originalComponentWillUnmount.apply(this);
      }
    };
    
    // 设置显示名称
    Component.displayName = `PerformanceOptimized(${componentName})`;
    
    return Component;
  };
}

export default withPerformanceOptimization;
