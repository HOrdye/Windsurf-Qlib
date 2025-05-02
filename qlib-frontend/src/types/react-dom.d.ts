declare module 'react-dom/client' {
  import * as React from 'react';
  
  /**
   * 创建一个根容器，用于在指定DOM节点中渲染React元素
   */
  export function createRoot(
    container: Element | DocumentFragment,
    options?: {
      onRecoverableError?: (error: any) => void;
      identifierPrefix?: string;
    }
  ): {
    render(children: React.ReactNode): void;
    unmount(): void;
  };
  
  /**
   * 创建一个支持hydration的根容器，用于在SSR环境中
   */
  export function hydrateRoot(
    container: Element | DocumentFragment,
    initialChildren: React.ReactNode,
    options?: {
      onRecoverableError?: (error: any) => void;
      identifierPrefix?: string;
    }
  ): {
    render(children: React.ReactNode): void;
    unmount(): void;
  };
}
