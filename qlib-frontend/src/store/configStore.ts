import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import * as YAML from 'yaml';

// 配置项类型
export interface ConfigItem {
  id: string;
  name: string;
  description: string;
  content: string;
  type: string;
  version: string;
  isDefault: boolean;
  favorite: boolean;
  createdAt: number;
  updatedAt: number;
}

// 配置快照类型
export interface ConfigSnapshot {
  id: string;
  name: string;
  content: string;
  timestamp: number;
  comment?: string;
}

// 配置模板类型
export interface ConfigTemplate {
  id: string;
  name: string;
  description: string;
  content: string;
  category: string;
  isBuiltIn: boolean;
  createdAt: number;
}

// 验证错误类型
export interface ValidationError {
  path: string;
  message: string;
  severity: 'error' | 'warning' | 'info';
}

// 配置状态接口
export interface ConfigState {
  currentConfig: string;
  configName: string;
  snapshots: ConfigSnapshot[];
  templates: ConfigTemplate[];
  isValidYaml: boolean;
  yamlError: string | null;
  validationErrors: ValidationError[];
  setCurrentConfig: (config: string) => void;
  setConfigName: (name: string) => void;
  saveSnapshot: (comment?: string) => boolean;
  loadSnapshot: (id: string) => boolean;
  deleteSnapshot: (id: string) => void;
  validateYaml: (content: string) => boolean;
  performAdvancedValidation: (content: string) => ValidationError[];
  saveTemplate: (name: string, description: string, category: string) => boolean;
  loadTemplate: (id: string) => boolean;
  deleteTemplate: (id: string) => void;
  importTemplate: (template: ConfigTemplate) => void;
  exportTemplates: () => ConfigTemplate[];
  getConfigById: (id: string) => ConfigTemplate | undefined;
}

// 默认配置模板
const DEFAULT_CONFIG = `qlib_init:
  provider_uri: "~/.qlib/qlib_data/cn_data"
  region: "cn"

market: &market
  dataset_provider: "LocalProvider"
  dataset: "csi300"
  start_time: "2008-01-01"
  end_time: "2020-08-01"
  
task:
  model:
    class: "LGBModel"
    module_path: "qlib.contrib.model.gbdt"
    kwargs:
      loss: "mse"
      colsample_bytree: 0.8879
      learning_rate: 0.0421
      subsample: 0.8789
      lambda_l1: 205.6999
      lambda_l2: 580.9768
      max_depth: 8
      num_leaves: 210
      
  dataset:
    class: "DatasetH"
    module_path: "qlib.data.dataset"
    kwargs:
      handler:
        class: "Alpha158"
        module_path: "qlib.contrib.data.handler"
        kwargs: *market
      segments:
        train: [2008-01-01, 2014-12-31]
        valid: [2015-01-01, 2016-12-31]
        test: [2017-01-01, 2020-08-01]
        
  record: 
    save_path: "benchmarks/results/LightGBM.pkl"`

// 内置模板
const BUILT_IN_TEMPLATES: ConfigTemplate[] = [
  {
    id: 'basic-lgbm',
    name: '基础LightGBM配置',
    description: '使用LightGBM模型的基础配置',
    content: DEFAULT_CONFIG,
    category: '基础模型',
    isBuiltIn: true,
    createdAt: Date.now()
  },
  {
    id: 'tuning-lgbm',
    name: 'LightGBM参数调优',
    description: '包含超参数调优设置的LightGBM配置',
    content: `qlib_init:
  provider_uri: "~/.qlib/qlib_data/cn_data"
  region: "cn"

task:
  model:
    class: "LGBModel"
    module_path: "qlib.contrib.model.gbdt"
    kwargs:
      loss: "mse"
      learning_rate: 0.01
      n_estimators: 100
      num_leaves: 31
      max_depth: -1
      
  # 超参数调优设置
  tuner:
    class: "OptunaOptimizer"
    module_path: "qlib.model.trainer"
    kwargs:
      # 优化目标
      optim_params:
        n_trials: 50
        timeout: 3600
        study_kwargs:
          sampler: "TPESampler"
        # 超参数搜索空间
        params:
          learning_rate:
            type: "float"
            min: 0.01
            max: 0.1
          n_estimators:
            type: "int"
            min: 50
            max: 500
          num_leaves:
            type: "int"
            min: 15
            max: 127
          max_depth:
            type: "int"
            min: 3
            max: 12`,
    category: '参数调优',
    isBuiltIn: true,
    createdAt: Date.now()
  },
  {
    id: 'xgboost-basic',
    name: '基础XGBoost配置',
    description: '使用XGBoost模型的基础配置',
    content: `qlib_init:
  provider_uri: "~/.qlib/qlib_data/cn_data"
  region: "cn"

market: &market
  dataset_provider: "LocalProvider"
  dataset: "csi300"
  start_time: "2008-01-01"
  end_time: "2020-08-01"
  
task:
  model:
    class: "XGBModel"
    module_path: "qlib.contrib.model.xgboost"
    kwargs:
      objective: "reg:squarederror"
      eta: 0.1
      max_depth: 6
      gamma: 0
      min_child_weight: 1
      subsample: 0.8
      colsample_bytree: 0.8
      
  dataset:
    class: "DatasetH"
    module_path: "qlib.data.dataset"
    kwargs:
      handler:
        class: "Alpha158"
        module_path: "qlib.contrib.data.handler"
        kwargs: *market
      segments:
        train: [2008-01-01, 2014-12-31]
        valid: [2015-01-01, 2016-12-31]
        test: [2017-01-01, 2020-08-01]
        
  record: 
    save_path: "benchmarks/results/XGBoost.pkl"`,
    category: '基础模型',
    isBuiltIn: true,
    createdAt: Date.now()
  }
];

// 创建配置状态管理
export const useConfigStore = create(
  persist(
    (set, get) => ({
      currentConfig: DEFAULT_CONFIG,
      configName: '默认配置',
      snapshots: [],
      templates: BUILT_IN_TEMPLATES,
      isValidYaml: true,
      yamlError: null,
      validationErrors: [],
      
      setCurrentConfig: (config: string) => {
        const isValid = get().validateYaml(config);
        const validationErrors = isValid ? get().performAdvancedValidation(config) : [];
        set({ 
          currentConfig: config,
          isValidYaml: isValid,
          validationErrors
        });
      },
      
      setConfigName: (name: string) => {
        set({ configName: name });
      },
      
      saveSnapshot: (comment?: string) => {
        const { currentConfig, configName, snapshots } = get();
        
        // 验证YAML
        if (!get().validateYaml(currentConfig)) {
          return false;
        }
        
        // 创建新快照
        const newSnapshot: ConfigSnapshot = {
          id: Date.now().toString(),
          name: configName,
          content: currentConfig,
          timestamp: Date.now(),
          comment
        };
        
        // 更新快照列表
        set({ 
          snapshots: [...snapshots, newSnapshot] 
        });
        
        return true;
      },
      
      loadSnapshot: (id: string) => {
        const { snapshots } = get();
        const snapshot = snapshots.find(s => s.id === id);
        
        if (snapshot) {
          const isValid = get().validateYaml(snapshot.content);
          const validationErrors = isValid ? get().performAdvancedValidation(snapshot.content) : [];
          
          set({ 
            currentConfig: snapshot.content,
            configName: snapshot.name,
            isValidYaml: isValid,
            yamlError: null,
            validationErrors
          });
          return true;
        }
        
        return false;
      },
      
      deleteSnapshot: (id: string) => {
        const { snapshots } = get();
        set({ 
          snapshots: snapshots.filter(s => s.id !== id) 
        });
      },
      
      validateYaml: (content: string) => {
        try {
          YAML.parse(content);
          set({ isValidYaml: true, yamlError: null });
          return true;
        } catch (e) {
          if (e instanceof Error) {
            set({ isValidYaml: false, yamlError: e.message });
          }
          return false;
        }
      },
      
      performAdvancedValidation: (content: string) => {
        const errors: ValidationError[] = [];
        
        try {
          const config = YAML.parse(content);
          
          // 检查必要的顶级字段
          if (!config.qlib_init) {
            errors.push({
              path: 'qlib_init',
              message: '缺少必要的qlib_init配置',
              severity: 'error'
            });
          } else {
            // 检查qlib_init必要字段
            if (!config.qlib_init.provider_uri) {
              errors.push({
                path: 'qlib_init.provider_uri',
                message: '缺少数据源路径配置',
                severity: 'error'
              });
            }
          }
          
          // 检查task配置
          if (!config.task) {
            errors.push({
              path: 'task',
              message: '缺少任务配置',
              severity: 'error'
            });
          } else {
            // 检查模型配置
            if (!config.task.model) {
              errors.push({
                path: 'task.model',
                message: '缺少模型配置',
                severity: 'error'
              });
            } else {
              if (!config.task.model.class) {
                errors.push({
                  path: 'task.model.class',
                  message: '缺少模型类名',
                  severity: 'error'
                });
              }
              
              if (!config.task.model.module_path) {
                errors.push({
                  path: 'task.model.module_path',
                  message: '缺少模型模块路径',
                  severity: 'error'
                });
              }
            }
            
            // 检查数据集配置
            if (!config.task.dataset) {
              errors.push({
                path: 'task.dataset',
                message: '缺少数据集配置',
                severity: 'warning'
              });
            } else {
              // 检查数据集分段
              if (config.task.dataset.kwargs && config.task.dataset.kwargs.segments) {
                const segments = config.task.dataset.kwargs.segments;
                
                // 检查训练集
                if (!segments.train) {
                  errors.push({
                    path: 'task.dataset.kwargs.segments.train',
                    message: '缺少训练集时间段配置',
                    severity: 'warning'
                  });
                }
                
                // 检查验证集
                if (!segments.valid) {
                  errors.push({
                    path: 'task.dataset.kwargs.segments.valid',
                    message: '缺少验证集时间段配置',
                    severity: 'warning'
                  });
                }
                
                // 检查测试集
                if (!segments.test) {
                  errors.push({
                    path: 'task.dataset.kwargs.segments.test',
                    message: '缺少测试集时间段配置',
                    severity: 'warning'
                  });
                }
              }
            }
          }
          
          // 检查市场数据配置
          if (config.market) {
            // 检查时间范围
            if (config.market.start_time && config.market.end_time) {
              try {
                const startDate = new Date(config.market.start_time);
                const endDate = new Date(config.market.end_time);
                
                if (startDate >= endDate) {
                  errors.push({
                    path: 'market.start_time/end_time',
                    message: '开始时间应早于结束时间',
                    severity: 'error'
                  });
                }
              } catch (e) {
                errors.push({
                  path: 'market.start_time/end_time',
                  message: '时间格式无效',
                  severity: 'error'
                });
              }
            }
          }
          
          set({ validationErrors: errors });
          return errors;
        } catch (e) {
          // 如果解析失败，返回空错误列表，因为基础验证已经捕获了语法错误
          return [];
        }
      },
      
      saveTemplate: (name: string, description: string, category: string) => {
        const { currentConfig, templates } = get();
        
        // 验证YAML
        if (!get().validateYaml(currentConfig)) {
          return false;
        }
        
        // 创建新模板
        const newTemplate: ConfigTemplate = {
          id: Date.now().toString(),
          name,
          description,
          content: currentConfig,
          category,
          isBuiltIn: false,
          createdAt: Date.now()
        };
        
        // 更新模板列表
        set({ 
          templates: [...templates, newTemplate] 
        });
        
        return true;
      },
      
      loadTemplate: (id: string) => {
        const { templates } = get();
        const template = templates.find(t => t.id === id);
        
        if (template) {
          const isValid = get().validateYaml(template.content);
          const validationErrors = isValid ? get().performAdvancedValidation(template.content) : [];
          
          set({ 
            currentConfig: template.content,
            configName: template.name,
            isValidYaml: isValid,
            yamlError: null,
            validationErrors
          });
          return true;
        }
        
        return false;
      },
      
      deleteTemplate: (id: string) => {
        const { templates } = get();
        // 只能删除非内置模板
        set({ 
          templates: templates.filter(t => t.id !== id || t.isBuiltIn) 
        });
      },
      
      importTemplate: (template: ConfigTemplate) => {
        const { templates } = get();
        // 确保导入的模板有唯一ID
        const newTemplate = {
          ...template,
          id: `imported-${Date.now()}-${Math.random().toString(36).substring(2, 9)}`,
          isBuiltIn: false,
          createdAt: Date.now()
        };
        
        set({
          templates: [...templates, newTemplate]
        });
      },
      
      exportTemplates: () => {
        const { templates } = get();
        // 返回用户创建的模板（非内置）
        return templates.filter(t => !t.isBuiltIn);
      },
      
      getConfigById: (id: string) => {
        const { templates } = get();
        const template = templates.find(t => t.id === id);
        return template;
      }
    }),
    {
      name: 'qlib-config-storage', // localStorage 的 key
      partialize: (state) => ({
        currentConfig: state.currentConfig,
        configName: state.configName,
        snapshots: state.snapshots,
        templates: state.templates // 保存所有模板，包括内置模板
      })
    }
  )
);
