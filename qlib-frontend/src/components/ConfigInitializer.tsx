import React, { useEffect } from 'react';
import { useConfigStore } from '../store/configStore';

/**
 * 配置初始化组件
 * 
 * 该组件负责确保配置存储中有可用的模板数据。
 * 如果检测到模板列表为空，将初始化内置模板。
 */
const ConfigInitializer: React.FC = () => {
  const { templates, importTemplate } = useConfigStore();

  useEffect(() => {
    // 检查是否需要初始化模板
    if (templates.length === 0) {
      console.log('正在初始化配置模板...');
      
      // 基础 LightGBM 模板
      importTemplate({
        id: 'basic-lgbm',
        name: '基础LightGBM配置',
        description: '使用LightGBM模型的基础配置',
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
    save_path: "benchmarks/results/LightGBM.pkl"`,
        category: '基础模型',
        isBuiltIn: true,
        createdAt: Date.now()
      });
      
      // LightGBM 参数调优模板
      importTemplate({
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
      });
      
      // XGBoost 基础模板
      importTemplate({
        id: 'xgboost-basic',
        name: 'XGBoost基础配置',
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
      });
      
      console.log('配置模板初始化完成');
    }
  }, [templates, importTemplate]);

  // 这是一个纯功能组件，不渲染任何内容
  return null;
};

export default ConfigInitializer;
