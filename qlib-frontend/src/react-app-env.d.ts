/// <reference types="react-scripts" />

/**
 * React 类型增强声明文件
 * 用于解决 React 18.3.1 与 TypeScript 类型定义的兼容性问题
 */

import * as React from 'react';

declare module 'react' {
  // 确保 lazy 和 Suspense 类型正确
  export const lazy: <T extends React.ComponentType<any>>(
    factory: () => Promise<{ default: T }>
  ) => T;

  export const Suspense: React.ComponentType<{
    children?: React.ReactNode;
    fallback: NonNullable<React.ReactNode>;
  }>;
}
