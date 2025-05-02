import * as React from 'react';

declare module 'react' {
  export = React;
  export as namespace React;
  
  // React 核心类型
  export type ReactNode = React.ReactNode;
  export type ReactElement = React.ReactElement;
  export type RefObject<T> = React.RefObject<T>;
  export type ComponentType<P = any> = React.ComponentType<P>;
  export type FC<P = {}> = React.FC<P>;
  export type FunctionComponent<P = {}> = React.FunctionComponent<P>;
  export type CSSProperties = React.CSSProperties;
  export type PropsWithChildren<P> = React.PropsWithChildren<P>;
  export type SyntheticEvent = React.SyntheticEvent;
  
  // React 钩子函数
  export function useState<T>(initialState: T | (() => T)): [T, React.Dispatch<React.SetStateAction<T>>];
  export function useEffect(effect: React.EffectCallback, deps?: React.DependencyList): void;
  export function useContext<T>(context: React.Context<T>): T;
  export function useReducer<R extends React.Reducer<any, any>, I>(
    reducer: R,
    initialArg: I,
    init?: (arg: I) => React.ReducerState<R>
  ): [React.ReducerState<R>, React.Dispatch<React.ReducerAction<R>>];
  export function useCallback<T extends (...args: any[]) => any>(
    callback: T,
    deps: React.DependencyList
  ): T;
  export function useMemo<T>(factory: () => T, deps: React.DependencyList | undefined): T;
  export function useRef<T>(initialValue: T): React.RefObject<T>;
  export function useImperativeHandle<T, R extends T>(
    ref: React.Ref<T> | undefined,
    init: () => R,
    deps?: React.DependencyList
  ): void;
  export function useLayoutEffect(
    effect: React.EffectCallback,
    deps?: React.DependencyList
  ): void;
  export function useDebugValue<T>(value: T, format?: (value: T) => any): void;
  
  // 类型辅助函数
  export function createContext<T>(defaultValue: T): React.Context<T>;
  export function createElement(
    type: string | React.ComponentType,
    props?: any,
    ...children: React.ReactNode[]
  ): React.ReactElement;
  
  // React 类型定义
  export type FC<P = {}> = React.FunctionComponent<P>;
  export type FunctionComponent<P = {}> = React.ComponentType<P>;
  export type ComponentType<P = {}> = React.ComponentClass<P> | React.FunctionComponent<P>;
  export interface FunctionComponent<P = {}> {
    (props: P, context?: any): React.ReactElement<any, any> | null;
    displayName?: string;
    propTypes?: any;
    contextTypes?: any;
    defaultProps?: Partial<P>;
  }
  export interface ComponentClass<P = {}, S = any> extends StaticLifecycle<P, S> {
    new(props: P, context?: any): React.Component<P, S>;
    propTypes?: any;
    contextTypes?: any;
    defaultProps?: Partial<P>;
    displayName?: string;
  }
  export interface StaticLifecycle<P, S> {
    getDerivedStateFromProps?: (props: P, state: S) => Partial<S> | null;
    getDerivedStateFromError?: (error: any) => Partial<S> | null;
  }
  export interface Component<P = {}, S = {}, SS = any> {
    render(): ReactNode;
    props: Readonly<P> & Readonly<{ children?: ReactNode | undefined }>;
    state: Readonly<S>;
    refs: {
      [key: string]: ReactInstance;
    };
  }
}

// 补充 JSX 命名空间
declare namespace JSX {
  interface Element extends React.ReactElement {}
  interface ElementClass extends React.Component<any> {
    render(): React.ReactNode;
  }
  interface ElementAttributesProperty {
    props: {};
  }
  interface ElementChildrenAttribute {
    children: {};
  }
  interface IntrinsicElements {
    [elemName: string]: any;
  }
}
