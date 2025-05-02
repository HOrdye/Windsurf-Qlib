/**
 * 数据预加载组件
 * 用于在后台预加载可能需要的数据，提升用户体验
 */

import React, { useEffect } from 'react';
import { useLocation } from 'react-router-dom';
import { dataPrefetchService } from '../services/performanceService';
import CacheService from '../services/cacheService';

interface PrefetchRule {
  // 当前路径匹配规则
  pathPattern: RegExp;
  // 需要预加载的数据获取函数
  prefetchFunctions: Array<{
    key: string;
    fetchFunc: () => Promise<any>;
    priority: number;
  }>;
}

interface DataPrefetcherProps {
  rules: PrefetchRule[];
  children?: React.ReactNode;
}

/**
 * 数据预加载组件
 * 根据当前路由和预定义规则，预加载可能需要的数据
 */
function DataPrefetcher({ rules, children }: DataPrefetcherProps) {
  const location = useLocation();

  // 根据当前路径执行预加载
  useEffect(() => {
    const currentPath = location.pathname;
    
    // 查找匹配的规则
    const matchingRules = rules.filter(rule => rule.pathPattern.test(currentPath));
    
    // 执行匹配规则的预加载函数
    matchingRules.forEach(rule => {
      rule.prefetchFunctions.forEach(({ key, fetchFunc, priority }) => {
        dataPrefetchService.addPrefetchTask(key, fetchFunc, priority);
      });
    });
    
    // 记录页面访问历史，用于智能预加载
    const pageHistory = CacheService.getUIPreferences().pageHistory || [];
    
    // 添加当前页面到历史
    pageHistory.unshift({
      path: currentPath,
      timestamp: Date.now()
    });
    
    // 限制历史记录长度
    if (pageHistory.length > 20) {
      pageHistory.pop();
    }
    
    // 保存更新后的历史记录
    CacheService.saveUIPreferences({
      ...CacheService.getUIPreferences(),
      pageHistory
    });
    
  }, [location.pathname, rules]);

  return <>{children}</>;
};

/**
 * 创建常用数据预加载规则
 * @returns 预加载规则数组
 */
export const createDefaultPrefetchRules = (): PrefetchRule[] => {
  return [
    // 仪表盘页面 - 预加载任务列表和配置列表
    {
      pathPattern: /^\/dashboard$/,
      prefetchFunctions: [
        {
          key: 'recentTasks',
          fetchFunc: async () => {
            // 从缓存获取最近任务
            return CacheService.IndexedDBService.getAll('taskResults');
          },
          priority: 8
        },
        {
          key: 'frequentConfigs',
          fetchFunc: async () => {
            // 获取常用配置
            return CacheService.getFrequentDatasets();
          },
          priority: 7
        }
      ]
    },
    
    // 配置编辑器页面 - 预加载模板和快照
    {
      pathPattern: /^\/config-editor/,
      prefetchFunctions: [
        {
          key: 'configTemplates',
          fetchFunc: async () => {
            // 获取配置模板
            return CacheService.IndexedDBService.getAll('configTemplates');
          },
          priority: 9
        },
        {
          key: 'configSnapshots',
          fetchFunc: async () => {
            // 获取配置快照
            return CacheService.IndexedDBService.getAll('configSnapshots');
          },
          priority: 8
        }
      ]
    },
    
    // 任务监控页面 - 预加载任务状态
    {
      pathPattern: /^\/task-monitor/,
      prefetchFunctions: [
        {
          key: 'taskStatus',
          fetchFunc: async () => {
            // 获取任务状态
            return CacheService.IndexedDBService.getAll('taskResults');
          },
          priority: 10
        }
      ]
    },
    
    // 回测结果页面 - 预加载数据集元数据
    {
      pathPattern: /^\/backtest-result/,
      prefetchFunctions: [
        {
          key: 'datasetMetadata',
          fetchFunc: async () => {
            // 获取数据集元数据
            return CacheService.IndexedDBService.getAll('datasetMetadata');
          },
          priority: 7
        }
      ]
    }
  ];
};

export default DataPrefetcher;
