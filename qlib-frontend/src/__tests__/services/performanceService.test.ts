/**
 * 性能优化服务单元测试
 */
import { 
  debounce, 
  throttle, 
  memoize, 
  performanceMonitor
} from '../../services/performanceService';
import { renderHook, act } from '@testing-library/react';

// 模拟定时器
jest.useFakeTimers();

describe('性能优化工具函数测试', () => {
  // 防抖函数测试
  describe('debounce', () => {
    test('应该在指定延迟后只执行一次函数', () => {
      const mockFn = jest.fn();
      const debouncedFn = debounce(mockFn, 1000);
      
      // 多次调用
      debouncedFn();
      debouncedFn();
      debouncedFn();
      
      // 验证函数尚未被调用
      expect(mockFn).not.toBeCalled();
      
      // 快进时间
      jest.advanceTimersByTime(1000);
      
      // 验证函数被调用一次
      expect(mockFn).toBeCalledTimes(1);
    });
    
    test('应该支持取消功能', () => {
      const mockFn = jest.fn();
      const debouncedFn = debounce(mockFn, 1000);
      
      debouncedFn();
      debouncedFn.cancel();
      
      // 快进时间
      jest.advanceTimersByTime(1000);
      
      // 验证函数未被调用
      expect(mockFn).not.toBeCalled();
    });
    
    test('immediate参数为true时应该立即执行函数', () => {
      const mockFn = jest.fn();
      const debouncedFn = debounce(mockFn, 1000, true);
      
      debouncedFn();
      
      // 验证函数立即被调用
      expect(mockFn).toBeCalledTimes(1);
      
      // 多次调用不应增加调用次数
      debouncedFn();
      debouncedFn();
      
      expect(mockFn).toBeCalledTimes(1);
      
      // 快进时间后再次调用应该再次执行
      jest.advanceTimersByTime(1000);
      debouncedFn();
      
      expect(mockFn).toBeCalledTimes(2);
    });
  });
  
  // 节流函数测试
  describe('throttle', () => {
    test('应该限制函数执行频率', () => {
      const mockFn = jest.fn();
      const throttledFn = throttle(mockFn, 1000);
      
      // 第一次调用应该立即执行
      throttledFn();
      expect(mockFn).toBeCalledTimes(1);
      
      // 在节流时间内的调用不应执行
      throttledFn();
      throttledFn();
      expect(mockFn).toBeCalledTimes(1);
      
      // 快进时间
      jest.advanceTimersByTime(1000);
      
      // 应该执行一次尾部调用
      expect(mockFn).toBeCalledTimes(2);
      
      // 再次调用应该立即执行
      throttledFn();
      expect(mockFn).toBeCalledTimes(3);
    });
    
    test('应该支持取消功能', () => {
      const mockFn = jest.fn();
      const throttledFn = throttle(mockFn, 1000);
      
      throttledFn();
      expect(mockFn).toBeCalledTimes(1);
      
      throttledFn();
      throttledFn.cancel();
      
      // 快进时间
      jest.advanceTimersByTime(1000);
      
      // 验证尾部调用被取消
      expect(mockFn).toBeCalledTimes(1);
    });
    
    test('options参数应该正确控制首尾调用行为', () => {
      const mockFn = jest.fn();
      const throttledFn = throttle(mockFn, 1000, { leading: false, trailing: true });
      
      // 第一次调用不应立即执行
      throttledFn();
      expect(mockFn).not.toBeCalled();
      
      // 快进时间
      jest.advanceTimersByTime(1000);
      
      // 应该执行尾部调用
      expect(mockFn).toBeCalledTimes(1);
    });
  });
  
  // 记忆化函数测试
  describe('memoize', () => {
    test('应该缓存函数结果', () => {
      const mockFn = jest.fn().mockImplementation((a, b) => a + b);
      const memoizedFn = memoize(mockFn);
      
      // 第一次调用应该执行原函数
      expect(memoizedFn(1, 2)).toBe(3);
      expect(mockFn).toBeCalledTimes(1);
      
      // 相同参数的调用应该使用缓存
      expect(memoizedFn(1, 2)).toBe(3);
      expect(mockFn).toBeCalledTimes(1);
      
      // 不同参数的调用应该执行原函数
      expect(memoizedFn(2, 3)).toBe(5);
      expect(mockFn).toBeCalledTimes(2);
    });
    
    test('应该支持自定义缓存键生成器', () => {
      const mockFn = jest.fn().mockImplementation((obj) => obj.value);
      const keyGenerator = (obj: { id: number, value: number }) => obj.id.toString();
      const memoizedFn = memoize(mockFn, keyGenerator);
      
      const obj1 = { id: 1, value: 10 };
      const obj2 = { id: 1, value: 20 }; // 相同id，不同value
      
      // 第一次调用
      expect(memoizedFn(obj1)).toBe(10);
      expect(mockFn).toBeCalledTimes(1);
      
      // 虽然value不同，但id相同，应该使用缓存
      expect(memoizedFn(obj2)).toBe(10); // 注意这里返回的是缓存的值10，而不是20
      expect(mockFn).toBeCalledTimes(1);
    });
  });
  
  // 性能监控服务测试
  describe('performanceMonitor', () => {
    test('应该能记录渲染时间', () => {
      // 模拟performance.now
      const originalNow = performance.now;
      performance.now = jest.fn()
        .mockReturnValueOnce(100) // 开始时间
        .mockReturnValueOnce(120); // 结束时间，渲染耗时20ms
      
      // 记录渲染时间
      performanceMonitor.recordRenderTime('TestComponent', 20);
      
      // 获取指标
      const metrics = performanceMonitor.getMetrics();
      
      // 验证渲染时间被记录
      expect(metrics.renderTime).toContain(20);
      
      // 恢复原始函数
      performance.now = originalNow;
    });
  });
});
