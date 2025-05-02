// 声明所有用到的外部模块，使用通配符
declare module 'react' {
  export * from 'react';
}
declare module 'react-dom';
declare module 'react/jsx-runtime';
declare module 'react-router-dom';
declare module 'antd';
declare module '@ant-design/icons';
declare module '@monaco-editor/react';
declare module 'yaml';
declare module 'zustand';
declare module 'zustand/middleware';
declare module 'echarts';
declare module 'echarts-for-react';
declare module 'socket.io-client';

// 声明全局的JSX命名空间
declare namespace JSX {
  interface Element {}
  interface IntrinsicElements {
    [elemName: string]: any;
  }
}
