declare module 'echarts' {
  export function init(
    dom: HTMLElement,
    theme?: string | object,
    opts?: {
      renderer?: 'canvas' | 'svg';
      devicePixelRatio?: number;
      width?: number | string;
      height?: number | string;
      locale?: string;
    }
  ): ECharts;

  export function connect(group: string | ECharts[]): void;
  export function disConnect(group: string): void;
  export function dispose(chart: ECharts | HTMLElement): void;
  export function getInstanceByDom(dom: HTMLElement): ECharts;
  export function registerMap(mapName: string, geoJson: object, specialAreas?: object): void;
  export function registerTheme(themeName: string, theme: object): void;
  export function registerLocale(locale: string, localeCfg: object): void;

  export interface ECharts {
    group: string;
    setOption(option: any, notMerge?: boolean, lazyUpdate?: boolean): void;
    getWidth(): number;
    getHeight(): number;
    getDom(): HTMLElement;
    getOption(): any;
    resize(opts?: { width?: number | string; height?: number | string; silent?: boolean }): void;
    dispatchAction(payload: object): void;
    on(eventName: string, handler: Function, context?: object): void;
    off(eventName: string, handler?: Function): void;
    convertToPixel(finder: object, value: any): number | number[];
    convertFromPixel(finder: object, value: any): number | number[];
    containPixel(finder: object, value: any): boolean;
    showLoading(type?: string, opts?: object): void;
    hideLoading(): void;
    getDataURL(opts: { type?: string; pixelRatio?: number; backgroundColor?: string; excludeComponents?: string[] }): string;
    getConnectedDataURL(opts: { type?: string; pixelRatio?: number; backgroundColor?: string; excludeComponents?: string[] }): string;
    appendData(opts: { seriesIndex?: number; data?: any[]; }): void;
    clear(): void;
    isDisposed(): boolean;
    dispose(): void;
  }

  export const graphic: any;
  export const dataTool: any;
  export const format: any;
  export const number: any;
  export const time: any;
  export const util: any;
  export const color: any;
}

declare module 'echarts-for-react' {
  import * as React from 'react';
  import { ECharts } from 'echarts';

  export interface ReactEChartsProps {
    option: any;
    notMerge?: boolean;
    lazyUpdate?: boolean;
    style?: React.CSSProperties;
    className?: string;
    theme?: string | object;
    onChartReady?: (echarts: ECharts) => void;
    onEvents?: Record<string, Function>;
    opts?: {
      renderer?: 'canvas' | 'svg';
      devicePixelRatio?: number;
      width?: number | string;
      height?: number | string;
      locale?: string;
    };
    showLoading?: boolean;
    loadingOption?: object;
  }
  
  export default class ReactECharts extends React.Component<ReactEChartsProps> {
    getEchartsInstance(): ECharts;
  }
}
