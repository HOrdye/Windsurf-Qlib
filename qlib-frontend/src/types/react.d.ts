declare module 'react' {
  export = React;
  export as namespace React;

  namespace React {
    interface FC<P = {}> {
      (props: P): ReactElement | null;
      displayName?: string;
    }

    type ReactNode = ReactElement | string | number | boolean | null | undefined | ReactNodeArray | ReactPortal;
    type ReactNodeArray = Array<ReactNode>;
    interface ReactPortal extends ReactElement {
      key: Key | null;
      children: ReactNode;
    }

    interface ReactElement<P = any, T extends string | JSXElementConstructor<any> = string | JSXElementConstructor<any>> {
      type: T;
      props: P;
      key: Key | null;
    }

    type JSXElementConstructor<P> = ((props: P) => ReactElement | null) | (new (props: P) => Component<P, any>);
    type Key = string | number;

    type RefCallback<T> = (instance: T | null) => void;
    type Ref<T> = RefCallback<T> | { current: T | null } | null;

    type ForwardRefRenderFunction<T, P = {}> = (props: P, ref: Ref<T>) => ReactElement | null;

    class Component<P = {}, S = {}> {
      constructor(props: P);
      state: S;
      props: P & { children?: ReactNode };
      setState(state: S | ((prevState: S, props: P) => S)): void;
      forceUpdate(): void;
      render(): ReactNode;
      context: any;
    }

    function useState<T>(initialState: T | (() => T)): [T, (newState: T | ((prevState: T) => T)) => void];
    function useEffect(effect: () => (void | (() => void)), deps?: ReadonlyArray<any>): void;
    function useRef<T>(initialValue: T): { current: T };
    function useCallback<T extends (...args: any[]) => any>(callback: T, deps: ReadonlyArray<any>): T;
    function useMemo<T>(factory: () => T, deps: ReadonlyArray<any>): T;
    function memo<P extends object>(
      Component: (props: P) => ReactElement | null,
      propsAreEqual?: (prevProps: Readonly<P>, nextProps: Readonly<P>) => boolean
    ): (props: P) => ReactElement | null;
    function forwardRef<T, P = {}>(
      render: ForwardRefRenderFunction<T, P>
    ): (props: P & { ref?: Ref<T> }) => ReactElement | null;
    function createElement<P extends {}>(
      type: string | JSXElementConstructor<P>,
      props?: P | null,
      ...children: ReactNode[]
    ): ReactElement<P>;
  }
}
