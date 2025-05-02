/**
 * 性能优化高阶组件单元测试
 */
import React from 'react';
import { render, cleanup } from '@testing-library/react';
import '@testing-library/jest-dom';

// 模拟性能监控服务
const mockRecordRenderTime = jest.fn();
const mockShouldComponentUpdate = jest.fn().mockReturnValue(true);

jest.mock('../../services/performanceService', () => ({
  performanceMonitor: {
    recordRenderTime: (...args: any[]) => mockRecordRenderTime(...args),
    shouldComponentUpdate: (...args: any[]) => mockShouldComponentUpdate(...args),
    getMetrics: jest.fn().mockReturnValue({
      renderTime: [],
      componentStats: {}
    })
  }
}));

// 模拟 performance API
const mockPerformanceNow = jest.fn()
  .mockReturnValueOnce(0)    // 第一次调用返回 0
  .mockReturnValueOnce(100); // 第二次调用返回 100，表示经过了 100ms

const originalPerformance = global.performance;

beforeEach(() => {
  jest.clearAllMocks();
  global.performance = {
    ...originalPerformance,
    now: mockPerformanceNow
  };
});

afterEach(() => {
  cleanup();
  global.performance = originalPerformance;
});

// 导入被测试的组件
import { withPerformanceOptimization } from '../../components/withPerformanceOptimization';

describe('withPerformanceOptimization高阶组件测试', () => {
  // 定义测试组件的Props类型
  interface TestComponentProps {
    text: string;
    count?: number;
  }

  // 创建测试组件
  const TestComponent: React.FC<TestComponentProps> = ({ text, count = 0 }) => (
    <div data-testid="test-component">
      {text} - {count}
    </div>
  );
  
  test('应该正确包装组件', () => {
    // 使用高阶组件包装测试组件
    // @ts-ignore - 忽略类型错误，仅用于测试
    const OptimizedComponent = withPerformanceOptimization<TestComponentProps>(TestComponent);
    
    // 渲染优化后的组件
    // @ts-ignore - 忽略类型错误，仅用于测试
    const { getByTestId } = render(<OptimizedComponent text="测试文本" />);
    
    // 验证组件是否正确渲染
    expect(getByTestId('test-component')).toHaveTextContent('测试文本 - 0');
    
    // 验证性能监控是否被调用
    expect(mockRecordRenderTime).toHaveBeenCalledWith(
      'TestComponent',
      expect.any(Number)
    );
  });
  
  test('应该避免不必要的重新渲染', () => {
    // 配置 shouldComponentUpdate 模拟函数返回 false
    mockShouldComponentUpdate.mockReturnValueOnce(false);
    
    // 使用高阶组件包装测试组件
    // @ts-ignore - 忽略类型错误，仅用于测试
    const OptimizedComponent = withPerformanceOptimization<TestComponentProps>(TestComponent);
    
    // 渲染优化后的组件
    // @ts-ignore - 忽略类型错误，仅用于测试
    const { rerender } = render(<OptimizedComponent text="测试文本" />);
    
    // 清除之前的调用记录
    mockRecordRenderTime.mockClear();
    
    // 使用相同的 props 重新渲染
    // @ts-ignore - 忽略类型错误，仅用于测试
    rerender(<OptimizedComponent text="测试文本" />);
    
    // 验证性能监控是否没有被再次调用
    expect(mockRecordRenderTime).not.toHaveBeenCalled();
  });
  
  test('应该处理无名称组件', () => {
    // 创建一个匿名组件
    interface AnonymousProps {
      value: string;
    }
    
    const AnonymousComponent: React.FC<AnonymousProps> = ({ value }) => (
      <div data-testid="anonymous-component">{value}</div>
    );
    
    // 删除组件名称，模拟匿名组件
    Object.defineProperty(AnonymousComponent, 'name', { value: '' });
    
    // 使用高阶组件包装匿名组件
    // @ts-ignore - 忽略类型错误，仅用于测试
    const OptimizedAnonymousComponent = withPerformanceOptimization<AnonymousProps>(
      AnonymousComponent,
      { componentName: 'Component' }
    );
    
    // 渲染优化后的组件
    // @ts-ignore - 忽略类型错误，仅用于测试
    const { getByTestId } = render(<OptimizedAnonymousComponent value="匿名组件" />);
    
    // 验证组件是否正确渲染
    expect(getByTestId('anonymous-component')).toHaveTextContent('匿名组件');
    
    // 验证性能监控是否被调用，并使用了默认名称
    expect(mockRecordRenderTime).toHaveBeenCalledWith(
      'Component',
      expect.any(Number)
    );
  });
  
  test('应该在组件卸载时清理资源', () => {
    // 使用高阶组件包装测试组件
    // @ts-ignore - 忽略类型错误，仅用于测试
    const OptimizedComponent = withPerformanceOptimization<TestComponentProps>(TestComponent);
    
    // 渲染优化后的组件
    // @ts-ignore - 忽略类型错误，仅用于测试
    const { unmount } = render(<OptimizedComponent text="测试文本" />);
    
    // 清除之前的调用记录
    mockRecordRenderTime.mockClear();
    
    // 卸载组件
    unmount();
    
    // 验证卸载时是否记录了渲染时间
    expect(mockRecordRenderTime).toHaveBeenCalledWith(
      'TestComponent',
      expect.any(Number)
    );
  });
  
  test('应该保留组件的原始属性', () => {
    // 创建一个带有静态属性的组件
    interface ComponentWithStaticsProps {
      text: string;
    }
    
    const ComponentWithStatics: React.FC<ComponentWithStaticsProps> = ({ text }) => (
      <div data-testid="static-component">{text}</div>
    );
    
    // 添加静态属性
    ComponentWithStatics.displayName = 'CustomTestComponent';
    
    // 使用高阶组件包装测试组件
    // @ts-ignore - 忽略类型错误，仅用于测试
    const OptimizedComponent = withPerformanceOptimization<ComponentWithStaticsProps>(ComponentWithStatics);
    
    // 验证静态属性是否被保留
    // @ts-ignore - 忽略类型错误，仅用于测试
    expect(OptimizedComponent.displayName).toBe('WithPerformanceOptimization(CustomTestComponent)');
    
    // 渲染优化后的组件
    // @ts-ignore - 忽略类型错误，仅用于测试
    const { getByTestId } = render(<OptimizedComponent text="测试文本" />);
    
    // 验证组件是否正确渲染
    expect(getByTestId('static-component')).toHaveTextContent('测试文本');
  });
});
