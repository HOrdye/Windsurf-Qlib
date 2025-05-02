declare module 'echarts-for-react' {
  import { Component } from 'react';
  import type { EChartsOption } from 'echarts';

  interface ReactEChartsProps {
    option: EChartsOption;
    notMerge?: boolean;
    lazyUpdate?: boolean;
    style?: React.CSSProperties;
    className?: string;
    theme?: string | object;
    onChartReady?: (instance: any) => void;
    onEvents?: Record<string, Function>;
    opts?: {
      devicePixelRatio?: number;
      renderer?: 'canvas' | 'svg';
      width?: number | string | null;
      height?: number | string | null;
    };
    loading?: boolean;
  }

  class ReactECharts extends Component<ReactEChartsProps> {
    getEchartsInstance(): any;
    render(): React.ReactNode;
  }

  const EChartsReactComponent: typeof ReactECharts;
  export = EChartsReactComponent;
}
