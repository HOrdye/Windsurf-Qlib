/**
 * 虚拟化表格组件
 * 用于高效渲染大量数据的表格
 */

import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Table, Spin } from 'antd';
import { useVirtualList, usePerformanceMonitoring } from '../services/performanceService';
import { debounce } from '../services/performanceService';
import './VirtualTable.css';

// 使用 any 类型来避免类型错误，但保留基本的类型安全性
interface VirtualTableProps<RecordType> {
  dataSource: RecordType[];
  columns: any[];
  rowHeight?: number;
  scrollY?: number;
  overscanRowCount?: number;
  loading?: boolean | { spinning: boolean; tip?: string; [key: string]: any };
  onLoadMore?: () => void;
  hasMore?: boolean;
  loadingMoreIndicator?: JSX.Element;
  virtualizationDisabled?: boolean;
  pagination?: any;
  scroll?: { x?: number; y?: number };
  [key: string]: any;
}

function VirtualTable<RecordType extends object = any>({
  dataSource,
  rowHeight = 54,
  scrollY = 400,
  overscanRowCount = 5,
  loading = false,
  onLoadMore,
  hasMore = false,
  loadingMoreIndicator = <div className="virtual-table-loading-more">加载更多数据...</div>,
  virtualizationDisabled = false,
  ...restProps
}: VirtualTableProps<RecordType>) {
  // 使用性能监控
  usePerformanceMonitoring('VirtualTable');

  // 表格容器引用
  const tableContainerRef = useRef<HTMLDivElement>(null);
  const [containerHeight, setContainerHeight] = useState<number>(scrollY);

  // 计算表格头部高度
  const [headerHeight, setHeaderHeight] = useState<number>(0);
  const headerRef = useRef<HTMLDivElement>(null);

  // 滚动位置
  const [scrollTop, setScrollTop] = useState(0);

  // 测量表格头部高度
  useEffect(() => {
    if (headerRef.current) {
      setHeaderHeight(headerRef.current.offsetHeight);
    }
  }, []);

  // 测量容器高度
  useEffect(() => {
    if (tableContainerRef.current) {
      const resizeObserver = new ResizeObserver((entries) => {
        for (const entry of entries) {
          setContainerHeight(entry.contentRect.height);
        }
      });

      resizeObserver.observe(tableContainerRef.current);
      return () => resizeObserver.disconnect();
    }
  }, []);

  // 处理滚动事件
  const handleScroll = useCallback(
    debounce((e: any) => {
      const scrollTop = e.currentTarget.scrollTop;
      setScrollTop(scrollTop);

      // 检查是否需要加载更多数据
      if (
        onLoadMore &&
        hasMore &&
        !loading &&
        e.currentTarget.scrollHeight - scrollTop - e.currentTarget.clientHeight < 200
      ) {
        onLoadMore();
      }
    }, 16),
    [onLoadMore, hasMore, loading]
  );

  // 计算可见区域
  const visibleHeight = containerHeight - headerHeight;

  // 使用虚拟列表
  const { virtualItems, totalHeight } = useMemo(() => {
    if (virtualizationDisabled) {
      return {
        virtualItems: dataSource.map((item, index) => ({
          index,
          item,
          offsetTop: index * rowHeight
        })),
        totalHeight: dataSource.length * rowHeight
      };
    }

    // 计算可见行的起始和结束索引
    const startIndex = Math.max(0, Math.floor(scrollTop / rowHeight) - overscanRowCount);
    const endIndex = Math.min(
      dataSource.length - 1,
      Math.floor((scrollTop + visibleHeight) / rowHeight) + overscanRowCount
    );

    // 生成虚拟项目
    const items = [];
    for (let i = startIndex; i <= endIndex; i++) {
      if (i < dataSource.length) {
        items.push({
          index: i,
          item: dataSource[i],
          offsetTop: i * rowHeight
        });
      }
    }

    return {
      virtualItems: items,
      totalHeight: dataSource.length * rowHeight
    };
  }, [dataSource, rowHeight, scrollTop, visibleHeight, overscanRowCount, virtualizationDisabled]);

  // 虚拟化数据源
  const virtualDataSource = useMemo(() => {
    return virtualItems.map(({ item }) => item);
  }, [virtualItems]);

  // 确定是否显示加载状态
  const isLoading = loading === true || (typeof loading === 'object' && loading.spinning !== false);

  // 表格组件
  return (
    <div
      ref={tableContainerRef}
      style={{ position: 'relative', height: scrollY, overflow: 'hidden' }}
      className="virtual-table-container"
    >
      <div
        style={{ height: '100%', overflow: 'auto' }}
        onScroll={handleScroll}
        className="virtual-table-scroll-container"
      >
        <div ref={headerRef} className="virtual-table-header-container">
          <Table
            {...restProps}
            dataSource={[]}
            pagination={false}
            className="virtual-table-header"
            showHeader={true}
          />
        </div>

        <div
          style={{
            height: totalHeight,
            position: 'relative',
            pointerEvents: isLoading ? 'none' : 'auto'
          }}
          className="virtual-table-body-container"
        >
          {virtualItems.map(({ index, offsetTop }) => (
            <div
              key={index}
              style={{
                position: 'absolute',
                top: offsetTop,
                width: '100%',
                height: rowHeight
              }}
              className="virtual-table-row-container"
            >
              <Table
                {...restProps}
                showHeader={false}
                dataSource={[dataSource[index]]}
                pagination={false}
                className="virtual-table-row"
              />
            </div>
          ))}

          {isLoading && (
            <div className="virtual-table-loading-overlay">
              {typeof loading === 'object' ? (
                <Spin {...loading} />
              ) : (
                <Spin size="large" />
              )}
            </div>
          )}

          {hasMore && !isLoading && onLoadMore && (
            <div
              style={{
                position: 'absolute',
                bottom: 0,
                width: '100%',
                textAlign: 'center',
                padding: '16px 0'
              }}
              className="virtual-table-load-more"
            >
              {loadingMoreIndicator}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default VirtualTable;
