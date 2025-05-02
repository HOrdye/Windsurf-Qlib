import React, { useState, useEffect, useRef } from 'react';
import { Card, Row, Col, Button, Space, message, Tabs, Select, Tooltip, Tag, Modal, Form, Input, Radio, Progress, List, Typography, Popconfirm, Empty, Alert } from 'antd';
import { 
  SaveOutlined, 
  PlayCircleOutlined, 
  FileTextOutlined, 
  HistoryOutlined,
  CopyOutlined,
  DownloadOutlined,
  QuestionCircleOutlined,
  SettingOutlined,
  StopOutlined,
  CheckCircleOutlined,
  ExclamationCircleOutlined,
  InfoCircleOutlined
} from '@ant-design/icons';
import MonacoEditor from '@monaco-editor/react';
import * as YAML from 'yaml';
import * as monaco from 'monaco-editor';
// 注释掉 monaco-yaml 的导入，我们将使用自定义的 YAML 支持
// import { configureMonacoYaml } from 'monaco-yaml';
import TaskManager from '../services/taskManager';
import WebSocketService, { MessageType } from '../services/websocket';
import { useConfigStore } from '../store/configStore';
import type { ValidationError, ConfigSnapshot, ConfigTemplate } from '../store/configStore';

const TEMPLATES: Record<string, string> = {
  basic: `qlib_init:
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
  lgbm_tuning: `qlib_init:
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
            max: 12`
};

const MODEL_CLASSES = [
  { label: 'LGBModel', detail: 'LightGBM模型', documentation: '基于树的梯度提升框架，高效、分布式、GPU支持' },
  { label: 'XGBModel', detail: 'XGBoost模型', documentation: '高效、灵活且可移植的分布式梯度提升库' },
  { label: 'LinearModel', detail: '线性模型', documentation: '基础线性回归/分类模型' },
  { label: 'MLP', detail: '多层感知机', documentation: '基础神经网络模型' },
  { label: 'LSTM', detail: '长短期记忆网络', documentation: '用于序列数据的循环神经网络' },
  { label: 'GRU', detail: '门控循环单元', documentation: 'LSTM的变体，计算效率更高' },
  { label: 'GATs', detail: '图注意力网络', documentation: '用于图数据的神经网络' },
  { label: 'TFT', detail: '时间融合Transformer', documentation: '用于时间序列预测的Transformer模型' }
];

const DATASET_CLASSES = [
  { label: 'DatasetH', detail: '分层数据集', documentation: 'Qlib标准分层数据集结构' },
  { label: 'TSDatasetH', detail: '时间序列数据集', documentation: '用于时间序列预测的数据集' },
  { label: 'DatasetProvider', detail: '数据集提供者', documentation: '通用数据集提供接口' }
];

const HANDLER_CLASSES = [
  { label: 'Alpha158', detail: '158个Alpha因子', documentation: 'Qlib预定义的158个Alpha因子特征' },
  { label: 'Alpha360', detail: '360个Alpha因子', documentation: 'Qlib预定义的360个Alpha因子特征' },
  { label: 'Alpha101', detail: '101个Alpha因子', documentation: '经典的101个Alpha因子特征' },
  { label: 'HighFreqHandler', detail: '高频数据处理器', documentation: '用于处理高频数据的特征提取器' }
];

const { TabPane } = Tabs;

const ConfigEditor = (): JSX.Element => {
  // 使用配置存储
  const { 
    currentConfig, 
    configName, 
    snapshots, 
    templates,
    isValidYaml, 
    yamlError, 
    validationErrors,
    setCurrentConfig, 
    setConfigName, 
    saveSnapshot, 
    loadSnapshot, 
    deleteSnapshot,
    validateYaml: storeValidateYaml,
    performAdvancedValidation: storePerformAdvancedValidation,
    saveTemplate,
    loadTemplate: storeLoadTemplate,
    deleteTemplate: storeDeleteTemplate,
    importTemplate,
    exportTemplates
  } = useConfigStore();

  // 编辑器状态
  const [code, setCode] = useState(currentConfig);
  const [errors, setErrors] = useState<ValidationError[]>([]);
  const [editorInstance, setEditorInstance] = useState<any>(null);
  const [monacoInstance, setMonacoInstance] = useState<any>(null);
  const [activeTab, setActiveTab] = useState('editor');
  const [isRunning, setIsRunning] = useState(false);
  const [taskId, setTaskId] = useState<string | null>(null);
  const [taskProgress, setTaskProgress] = useState(0);
  const [taskStatus, setTaskStatus] = useState('');
  const [showTemplateHelp, setShowTemplateHelp] = useState(false);
  const [isParameterTuningVisible, setParameterTuningVisible] = useState(false);
  const [templateManagerVisible, setTemplateManagerVisible] = useState(false);
  const [versionManagerVisible, setVersionManagerVisible] = useState(false);
  const [selectedModelType, setSelectedModelType] = useState('LGBModel');
  const [selectedTemplate, setSelectedTemplate] = useState('basic');
  
  // 模板管理状态
  const [templateName, setTemplateName] = useState('');
  const [templateDescription, setTemplateDescription] = useState('');
  const [templateCategory, setTemplateCategory] = useState('自定义');
  
  // 版本管理状态
  const [versionComment, setVersionComment] = useState('');

  // 表单引用
  const paramTuningFormRef = useRef<any>(null);
  const templateFormRef = useRef<any>(null);
  const versionFormRef = useRef<any>(null);

  // WebSocket服务
  const wsRef = useRef<WebSocketService | null>(null);

  // 初始化
  useEffect(() => {
    // 初始化WebSocket连接
    wsRef.current = WebSocketService.getInstance();
    wsRef.current.connect();
    
    // 设置WebSocket事件处理
    wsRef.current.on(MessageType.TASK_STATUS, (data: any) => {
      if (data.task_id === taskId) {
        handleTaskUpdate(data.task_id);
      }
    });
    
    // 清理函数
    return () => {
      if (wsRef.current) {
        wsRef.current.disconnect();
      }
    };
  }, [taskId]);

  // 当编辑器内容变化时更新状态
  useEffect(() => {
    // 更新配置存储
    setCurrentConfig(code);
    
    // 验证YAML
    if (isValidYaml) {
      setErrors(validationErrors);
    }
  }, [code, setCurrentConfig]);

  // 当配置名称变化时更新状态
  useEffect(() => {
    setConfigName(configName);
  }, [configName, setConfigName]);

  // 处理任务状态更新
  const handleTaskUpdate = (taskId: string) => {
    // 使用WebSocket服务获取任务状态
    wsRef.current?.request(MessageType.TASK_STATUS, {
      action: 'get',
      taskId
    })
      .then(response => {
        if (response && response.data) {
          const taskStatus = response.data;
          setTaskProgress(taskStatus.progress || 0);
          setTaskStatus(taskStatus.status || '');
          
          if (taskStatus.status === 'completed' || taskStatus.status === 'failed') {
            setIsRunning(false);
            if (taskStatus.status === 'completed') {
              message.success('任务执行成功');
            } else {
              message.error(`任务执行失败: ${taskStatus.error || '未知错误'}`);
            }
          }
        }
      })
      .catch(error => {
        console.error('获取任务状态失败:', error);
        message.error('获取任务状态失败');
      });
  };

  // 在编辑器初始化完成时设置引用
  const handleEditorDidMount = (editor: any, monaco: any) => {
    setEditorInstance(editor);
    setMonacoInstance(monaco);
    
    // 设置编辑器高级功能
    setupEditorFeatures(editor, monaco);
    
    // 初始验证
    const validationResult = storeValidateYaml(code);
    if (validationResult) {
      const advancedErrors = storePerformAdvancedValidation(code);
      setErrors(advancedErrors);
    }
  };

  // 增强 YAML 文档结构智能提示
  const getDocumentStructure = (yamlContent: string): any => {
    try {
      const parsed = YAML.parse(yamlContent);
      return parsed;
    } catch (e) {
      // 如果解析失败，返回空对象
      return {};
    }
  };

  // 分析 YAML 结构，返回当前光标所在的路径上下文
  const analyzeYamlContext = (editor: any): string => {
    if (!editor) return '';
    
    const position = editor.getPosition();
    if (!position) return '';
    
    const lineContent = editor.getModel().getLineContent(position.lineNumber);
    const lineUntilCursor = lineContent.substring(0, position.column - 1);
    
    // 计算缩进级别
    const indentMatch = lineUntilCursor.match(/^(\s*)/);
    const currentIndent = indentMatch ? indentMatch[1].length : 0;
    
    // 查找上下文路径
    let contextPath = '';
    let lineNumber = position.lineNumber - 1;
    
    while (lineNumber > 0) {
      const prevLine = editor.getModel().getLineContent(lineNumber);
      const prevIndentMatch = prevLine.match(/^(\s*)/);
      const prevIndent = prevIndentMatch ? prevIndentMatch[1].length : 0;
      
      // 如果找到缩进更少的行，说明是父级
      if (prevIndent < currentIndent && prevLine.trim().length > 0) {
        // 提取键名
        const keyMatch = prevLine.match(/^(\s*)([^:]+):/);
        if (keyMatch) {
          const key = keyMatch[2].trim();
          contextPath = contextPath ? `${key}.${contextPath}` : key;
          
          // 如果已经到达顶级，退出循环
          if (prevIndent === 0) {
            break;
          }
        }
      }
      
      lineNumber--;
    }
    
    return contextPath;
  };

  // 设置编辑器高级功能
  const setupEditorFeatures = (editor: any, monaco: any) => {
    // 注册自动完成提供程序
    monaco.languages.registerCompletionItemProvider('yaml', {
      provideCompletionItems: (model: any, position: any) => {
        const textUntilPosition = model.getValueInRange({
          startLineNumber: 1,
          startColumn: 1,
          endLineNumber: position.lineNumber,
          endColumn: position.column
        });
        
        // 获取当前上下文路径
        const contextPath = analyzeYamlContext(editor);
        
        // 基于上下文路径提供建议
        const suggestions = [];
        
        // 顶级字段建议
        if (!contextPath) {
          suggestions.push({
            label: 'qlib_init',
            kind: monaco.languages.CompletionItemKind.Field,
            insertText: 'qlib_init:\n  provider_uri: "${1:~/.qlib/qlib_data/cn_data}"\n  region: "${2:cn}"',
            insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
            documentation: 'Qlib初始化配置'
          });
          
          suggestions.push({
            label: 'market',
            kind: monaco.languages.CompletionItemKind.Field,
            insertText: 'market: ${1:&market}\n  dataset_provider: "${2:LocalProvider}"\n  dataset: "${3:csi300}"\n  start_time: "${4:2008-01-01}"\n  end_time: "${5:2020-08-01}"',
            insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
            documentation: '市场数据配置'
          });
          
          suggestions.push({
            label: 'task',
            kind: monaco.languages.CompletionItemKind.Field,
            insertText: 'task:\n  model:\n    class: "${1:LGBModel}"\n    module_path: "${2:qlib.contrib.model.gbdt}"\n    kwargs:\n      ${3:loss}: "${4:mse}"',
            insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
            documentation: '任务配置'
          });
        }
        
        // 模型相关建议
        if (contextPath.startsWith('task.model')) {
          // 模型类建议
          if (contextPath === 'task.model') {
            suggestions.push({
              label: 'class',
              kind: monaco.languages.CompletionItemKind.Field,
              insertText: 'class: "${1:LGBModel}"',
              insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
              documentation: '模型类名'
            });
            
            suggestions.push({
              label: 'module_path',
              kind: monaco.languages.CompletionItemKind.Field,
              insertText: 'module_path: "${1:qlib.contrib.model.gbdt}"',
              insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
              documentation: '模型模块路径'
            });
            
            suggestions.push({
              label: 'kwargs',
              kind: monaco.languages.CompletionItemKind.Field,
              insertText: 'kwargs:\n  ${1:loss}: "${2:mse}"',
              insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
              documentation: '模型参数'
            });
          }
          
          // 模型参数建议
          if (contextPath === 'task.model.kwargs') {
            // 根据选定的模型类型提供不同的参数建议
            if (selectedModelType === 'LGBModel') {
              suggestions.push({
                label: 'loss',
                kind: monaco.languages.CompletionItemKind.Property,
                insertText: 'loss: "${1:mse}"',
                insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                documentation: '损失函数类型'
              });
              
              suggestions.push({
                label: 'learning_rate',
                kind: monaco.languages.CompletionItemKind.Property,
                insertText: 'learning_rate: ${1:0.1}',
                insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                documentation: '学习率'
              });
              
              suggestions.push({
                label: 'max_depth',
                kind: monaco.languages.CompletionItemKind.Property,
                insertText: 'max_depth: ${1:8}',
                insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                documentation: '树的最大深度'
              });
            } else if (selectedModelType === 'XGBModel') {
              suggestions.push({
                label: 'objective',
                kind: monaco.languages.CompletionItemKind.Property,
                insertText: 'objective: "${1:reg:squarederror}"',
                insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                documentation: '优化目标'
              });
              
              suggestions.push({
                label: 'eta',
                kind: monaco.languages.CompletionItemKind.Property,
                insertText: 'eta: ${1:0.1}',
                insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                documentation: '学习率'
              });
            }
          }
        }
        
        // 数据集相关建议
        if (contextPath.startsWith('task.dataset')) {
          if (contextPath === 'task.dataset') {
            suggestions.push({
              label: 'class',
              kind: monaco.languages.CompletionItemKind.Field,
              insertText: 'class: "${1:DatasetH}"',
              insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
              documentation: '数据集类名'
            });
            
            suggestions.push({
              label: 'module_path',
              kind: monaco.languages.CompletionItemKind.Field,
              insertText: 'module_path: "${1:qlib.data.dataset}"',
              insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
              documentation: '数据集模块路径'
            });
          }
          
          if (contextPath === 'task.dataset.kwargs.segments') {
            suggestions.push({
              label: 'train',
              kind: monaco.languages.CompletionItemKind.Field,
              insertText: 'train: [${1:2008-01-01}, ${2:2014-12-31}]',
              insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
              documentation: '训练集时间段'
            });
            
            suggestions.push({
              label: 'valid',
              kind: monaco.languages.CompletionItemKind.Field,
              insertText: 'valid: [${1:2015-01-01}, ${2:2016-12-31}]',
              insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
              documentation: '验证集时间段'
            });
            
            suggestions.push({
              label: 'test',
              kind: monaco.languages.CompletionItemKind.Field,
              insertText: 'test: [${1:2017-01-01}, ${2:2020-08-01}]',
              insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
              documentation: '测试集时间段'
            });
          }
        }
        
        return {
          suggestions
        };
      }
    });
    
    // 添加错误标记功能
    editor.onDidChangeModelContent(() => {
      // 获取当前编辑器内容
      const content = editor.getValue();
      
      // 验证YAML
      const isValid = storeValidateYaml(content);
      
      // 如果有效，执行高级验证
      if (isValid) {
        const advancedErrors = storePerformAdvancedValidation(content);
        setErrors(advancedErrors);
        
        // 在编辑器中标记错误
        const markers = advancedErrors.map(error => {
          // 查找错误路径在文本中的位置
          const lines = content.split('\n');
          let lineNumber = 1;
          let column = 1;
          
          // 简单查找包含路径的行
          for (let i = 0; i < lines.length; i++) {
            if (lines[i].includes(error.path.split('.').pop() || '')) {
              lineNumber = i + 1;
              column = lines[i].indexOf(error.path.split('.').pop() || '') + 1;
              break;
            }
          }
          
          return {
            severity: error.severity === 'error' ? monaco.MarkerSeverity.Error : 
                      error.severity === 'warning' ? monaco.MarkerSeverity.Warning : 
                      monaco.MarkerSeverity.Info,
            message: error.message,
            startLineNumber: lineNumber,
            startColumn: column,
            endLineNumber: lineNumber,
            endColumn: column + (error.path.split('.').pop() || '').length
          };
        });
        
        monaco.editor.setModelMarkers(editor.getModel(), 'yaml-validation', markers);
      } else {
        // 清除高级验证错误
        setErrors([]);
        monaco.editor.setModelMarkers(editor.getModel(), 'yaml-validation', []);
      }
    });
  };

  // 高级YAML验证
  const validateYaml = (yamlContent: string): boolean => {
    try {
      YAML.parse(yamlContent);
      return true;
    } catch (e) {
      return false;
    }
  };

  // 执行高级验证
  const performAdvancedValidation = (config: any): ValidationError[] => {
    const errors: ValidationError[] = [];
    
    // 验证必要字段
    if (!config.task) {
      errors.push({
        path: 'task',
        message: '缺少必要的task配置部分',
        severity: 'error'
      });
    }
    
    // 验证模型配置
    if (config.task.model) {
      const model = config.task.model;
      if (!model.class) {
        errors.push({
          path: 'task.model.class',
          message: 'task.model缺少必要的class字段',
          severity: 'error'
        });
      }
      if (!model.module_path) {
        errors.push({
          path: 'task.model.module_path',
          message: 'task.model缺少必要的module_path字段',
          severity: 'error'
        });
      }
      
      // 验证模型类型
      const validModelClasses = MODEL_CLASSES.map(m => m.label);
      if (!validModelClasses.includes(model.class)) {
        errors.push({
          path: 'task.model.class',
          message: `不支持的模型类型: ${model.class}。支持的类型: ${validModelClasses.join(', ')}`,
          severity: 'error'
        });
      }
      
      // 验证模型参数
      if (model.class === 'LGBModel' && model.kwargs) {
        // LightGBM特定验证
        const { learning_rate, max_depth, num_leaves } = model.kwargs;
        
        if (learning_rate && (learning_rate < 0.001 || learning_rate > 1)) {
          errors.push({
            path: 'task.model.kwargs.learning_rate',
            message: 'learning_rate应在0.001到1之间',
            severity: 'warning'
          });
        }
        
        if (max_depth && max_depth < 3 && max_depth !== -1) {
          errors.push({
            path: 'task.model.kwargs.max_depth',
            message: 'max_depth应大于等于3或设为-1(无限制)',
            severity: 'warning'
          });
        }
        
        if (num_leaves && (num_leaves < 2 || num_leaves > 1000)) {
          errors.push({
            path: 'task.model.kwargs.num_leaves',
            message: 'num_leaves应在2到1000之间',
            severity: 'warning'
          });
        }
      }
    } else {
      errors.push({
        path: 'task.model',
        message: '缺少必要的task.model配置部分',
        severity: 'error'
      });
    }
    
    // 验证数据集配置
    if (config.task.dataset) {
      const dataset = config.task.dataset;
      if (!dataset.class) {
        errors.push({
          path: 'task.dataset.class',
          message: 'task.dataset缺少必要的class字段',
          severity: 'error'
        });
      }
      
      // 验证数据集分段
      if (dataset.segments) {
        const { train, valid, test } = dataset.segments;
        if (!train) {
          errors.push({
            path: 'task.dataset.segments.train',
            message: 'dataset.segments缺少必要的train分段',
            severity: 'error'
          });
        }
        
        // 验证日期格式和顺序
        const validateDateRange = (range: any): boolean => {
          if (!Array.isArray(range) || range.length !== 2) return false;
          
          // 简单日期格式验证
          const dateRegex = /^\d{4}-\d{2}-\d{2}$/;
          return dateRegex.test(range[0]) && dateRegex.test(range[1]);
        };
        
        if (!validateDateRange(train)) {
          errors.push({
            path: 'task.dataset.segments.train',
            message: 'train日期范围格式错误，应为[YYYY-MM-DD, YYYY-MM-DD]',
            severity: 'warning'
          });
        }
        
        if (valid && !validateDateRange(valid)) {
          errors.push({
            path: 'task.dataset.segments.valid',
            message: 'valid日期范围格式错误，应为[YYYY-MM-DD, YYYY-MM-DD]',
            severity: 'warning'
          });
        }
        
        if (test && !validateDateRange(test)) {
          errors.push({
            path: 'task.dataset.segments.test',
            message: 'test日期范围格式错误，应为[YYYY-MM-DD, YYYY-MM-DD]',
            severity: 'warning'
          });
        }
      } else {
        errors.push({
          path: 'task.dataset.segments',
          message: 'task.dataset缺少必要的segments配置',
          severity: 'error'
        });
      }
    } else {
      errors.push({
        path: 'task.dataset',
        message: '缺少必要的task.dataset配置部分',
        severity: 'error'
      });
    }
    
    return errors;
  };

  // 打开参数调优工具
  const openParameterTuning = () => {
    // 分析当前YAML内容，提取模型参数
    try {
      const parsed = YAML.parse(code);
      if (parsed?.task?.model?.class && MODEL_CLASSES.find(m => m.label === parsed.task.model.class)) {
        setSelectedModelType(parsed.task.model.class);
        setParameterTuningVisible(true);
      } else {
        message.warning('请先在配置中指定有效的模型类');
      }
    } catch (e) {
      message.error('无法解析当前配置，请先修复YAML格式错误');
    }
  };

  // 处理参数调优表单提交
  const handleParameterTuningSubmit = (values: any) => {
    try {
      const config = YAML.parse(code);
      if (config?.task?.model?.kwargs) {
        config.task.model.kwargs = { ...config.task.model.kwargs, ...values };
        const newCode = YAML.stringify(config);
        setCode(newCode);
        message.success('参数已更新');
      }
    } catch (e) {
      message.error('更新参数失败');
      console.error(e);
    }
    setParameterTuningVisible(false);
  };

  // 渲染参数调优表单
  const renderParameterTuningForm = () => {
    const modelConfig = MODEL_CLASSES.find(m => m.label === selectedModelType);
    if (!modelConfig) {
      return <div>请先选择模型类型</div>;
    }

    return (
      <Form
        layout="vertical"
        onFinish={handleParameterTuningSubmit}
        initialValues={{
          learning_rate: 0.1,
          max_depth: 8,
          num_leaves: 31
        }}
      >
        {modelConfig.label === 'LGBModel' && (
          <Form.Item 
            label="学习率" 
            name="learning_rate"
          >
            <Input 
              type="number" 
              step="0.01"
              min={0.001}
              max={1}
            />
          </Form.Item>
        )}
        
        {modelConfig.label === 'LGBModel' && (
          <Form.Item 
            label="树的最大深度" 
            name="max_depth"
          >
            <Input 
              type="number" 
              min={3}
              max={100}
            />
          </Form.Item>
        )}
        
        {modelConfig.label === 'LGBModel' && (
          <Form.Item 
            label="叶子节点数量" 
            name="num_leaves"
          >
            <Input 
              type="number" 
              min={2}
              max={1000}
            />
          </Form.Item>
        )}
        
        <Form.Item>
          <Button type="primary" htmlType="submit">
            应用参数
          </Button>
        </Form.Item>
      </Form>
    );
  };

  // 在Monaco Editor配置中添加YAML语言支持
  const handleEditorWillMount = (monaco: any) => {
    try {
      // 注册 YAML 语言
      monaco.languages.register({ id: 'yaml', extensions: ['.yml', '.yaml'] });
      
      // 配置 YAML 语法高亮
      monaco.languages.setMonarchTokensProvider('yaml', {
        tokenizer: {
          root: [
            [/---/, 'delimiter.yaml'],
            [/\.\.\./, 'delimiter.yaml'],
            [/#.*$/, 'comment'],
            [/('''|""")/, 'string', '@endDocString'],
            [/'[^']*'/, 'string'],
            [/"[^"]*"/, 'string'],
            [/\b(true|false|null)\b/, 'keyword'],
            [/\d+/, 'number'],
            [/:/, 'delimiter'],
            [/\w+/, 'identifier']
          ],
          endDocString: [
            [/([^\\]|\\.)'''/, 'string', '@pop'],
            [/([^\\]|\\.)"""/, 'string', '@pop']
          ]
        }
      });
      
      console.log('YAML 语言支持已配置');
    } catch (error) {
      console.error('编辑器配置错误:', error);
    }
  };

  // 添加模板管理相关函数
  const handleSaveAsTemplate = () => {
    if (!templateName) {
      message.error('请输入模板名称');
      return;
    }

    if (!storeValidateYaml(code)) {
      message.error('当前配置存在YAML语法错误，无法保存为模板');
      return;
    }
    
    // 使用配置存储的saveTemplate方法
    if (saveTemplate(templateName, templateDescription, templateCategory)) {
      message.success(`已保存模板: ${templateName}`);
      setTemplateName('');
      setTemplateDescription('');
      setTemplateManagerVisible(false);
    } else {
      message.error('保存模板失败');
    }
  };

  const handleDeleteTemplate = (id: string) => {
    // 使用配置存储的deleteTemplate方法
    storeDeleteTemplate(id);
    message.success('已删除模板');
  };

  const handleLoadTemplate = (id: string) => {
    try {
      // 使用配置存储的loadTemplate方法
      if (storeLoadTemplate(id)) {
        message.success('已加载模板');
      } else {
        message.error('加载模板失败');
      }
    } catch (e) {
      console.error('加载模板失败:', e);
      message.error('加载模板失败');
    }
  };

  // 添加版本管理相关函数
  const createVersionSnapshot = (comment: string = '') => {
    if (!storeValidateYaml(code)) {
      message.error('当前配置存在YAML语法错误，无法创建版本');
      return false;
    }
    
    // 使用配置存储的saveSnapshot方法
    if (saveSnapshot(comment)) {
      message.success('已创建新版本');
      return true;
    } else {
      message.error('创建版本失败');
      return false;
    }
  };

  const handleLoadVersionSnapshot = (id: string) => {
    try {
      // 使用配置存储的loadSnapshot方法
      if (loadSnapshot(id)) {
        message.success('已恢复到指定版本');
        return true;
      }
    } catch (e) {
      console.error('加载版本失败:', e);
    }
    
    message.error('加载版本失败');
    return false;
  };

  const handleDeleteVersionSnapshot = (id: string) => {
    try {
      // 使用配置存储的deleteSnapshot方法
      deleteSnapshot(id);
      message.success('已删除版本');
      return true;
    } catch (e) {
      console.error('删除版本失败:', e);
      message.error('删除版本失败');
      return false;
    }
  };

  // 在组件内部添加模板管理器对话框
  const renderTemplateManager = () => {
    return (
      <Modal
        title="模板管理"
        open={templateManagerVisible}
        onCancel={() => setTemplateManagerVisible(false)}
        footer={null}
        width={800}
      >
        <Tabs defaultActiveKey="save">
          <TabPane tab="保存模板" key="save">
            <Form layout="vertical">
              <Form.Item 
                label="模板名称" 
                required
                rules={[{ required: true, message: '请输入模板名称' }]}
              >
                <Input 
                  value={templateName}
                  onChange={e => setTemplateName(e.target.value)}
                  placeholder="输入模板名称"
                />
              </Form.Item>
              
              <Form.Item 
                label="模板描述"
              >
                <Input.TextArea 
                  value={templateDescription}
                  onChange={e => setTemplateDescription(e.target.value)}
                  placeholder="输入模板描述"
                  rows={3}
                />
              </Form.Item>
              
              <Form.Item 
                label="模板分类"
              >
                <Select 
                  value={templateCategory}
                  onChange={value => setTemplateCategory(value)}
                  style={{ width: '100%' }}
                >
                  <Select.Option value="自定义">自定义</Select.Option>
                  <Select.Option value="基础模型">基础模型</Select.Option>
                  <Select.Option value="参数调优">参数调优</Select.Option>
                  <Select.Option value="高级配置">高级配置</Select.Option>
                </Select>
              </Form.Item>
              
              <Form.Item>
                <Button type="primary" onClick={handleSaveAsTemplate}>
                  保存模板
                </Button>
              </Form.Item>
            </Form>
          </TabPane>
          
          <TabPane tab="管理模板" key="manage">
            <List
              dataSource={templates.filter(t => !t.isBuiltIn)}
              renderItem={template => (
                <List.Item
                  actions={[
                    <Button 
                      key="load" 
                      type="link" 
                      onClick={() => handleLoadTemplate(template.id)}
                    >
                      加载
                    </Button>,
                    <Popconfirm
                      key="delete"
                      title="确定要删除此模板吗？"
                      onConfirm={() => handleDeleteTemplate(template.id)}
                      okText="确定"
                      cancelText="取消"
                    >
                      <Button type="link" danger>删除</Button>
                    </Popconfirm>
                  ]}
                >
                  <List.Item.Meta
                    title={template.name}
                    description={
                      <>
                        <div>{template.description}</div>
                        <Tag color="blue">{template.category}</Tag>
                        <div style={{ fontSize: 12, color: '#999' }}>
                          创建时间: {new Date(template.createdAt).toLocaleString()}
                        </div>
                      </>
                    }
                  />
                </List.Item>
              )}
            />
          </TabPane>
          
          <TabPane tab="内置模板" key="builtin">
            <List
              dataSource={templates.filter(t => t.isBuiltIn)}
              renderItem={template => (
                <List.Item
                  actions={[
                    <Button 
                      key="load" 
                      type="link" 
                      onClick={() => handleLoadTemplate(template.id)}
                    >
                      加载
                    </Button>
                  ]}
                >
                  <List.Item.Meta
                    title={template.name}
                    description={
                      <>
                        <div>{template.description}</div>
                        <Tag color="green">{template.category}</Tag>
                      </>
                    }
                  />
                </List.Item>
              )}
            />
          </TabPane>
        </Tabs>
      </Modal>
    );
  };

  // 在组件内部添加版本管理对话框
  const renderVersionManager = () => {
    return (
      <Modal
        title="版本管理"
        open={versionManagerVisible}
        onCancel={() => setVersionManagerVisible(false)}
        footer={null}
        width={800}
      >
        <Tabs defaultActiveKey="create">
          <TabPane tab="创建版本" key="create">
            <Form layout="vertical">
              <Form.Item 
                label="版本备注"
              >
                <Input.TextArea 
                  value={versionComment}
                  onChange={e => setVersionComment(e.target.value)}
                  placeholder="输入版本备注（可选）"
                  rows={3}
                />
              </Form.Item>
              
              <Form.Item>
                <Button 
                  type="primary" 
                  onClick={() => {
                    if (createVersionSnapshot(versionComment)) {
                      setVersionComment('');
                      setVersionManagerVisible(false);
                    }
                  }}
                >
                  创建版本
                </Button>
              </Form.Item>
            </Form>
          </TabPane>
          
          <TabPane tab="管理版本" key="manage">
            <List
              dataSource={snapshots}
              renderItem={(snapshot: ConfigSnapshot) => (
                <List.Item
                  actions={[
                    <Button 
                      key="load" 
                      type="link" 
                      onClick={() => handleLoadVersionSnapshot(snapshot.id)}
                    >
                      恢复
                    </Button>,
                    <Popconfirm
                      key="delete"
                      title="确定要删除此版本吗？"
                      onConfirm={() => handleDeleteVersionSnapshot(snapshot.id)}
                      okText="确定"
                      cancelText="取消"
                    >
                      <Button type="link" danger>删除</Button>
                    </Popconfirm>
                  ]}
                >
                  <List.Item.Meta
                    title={snapshot.name}
                    description={
                      <>
                        {snapshot.comment && (
                          <div style={{ marginBottom: 8 }}>{snapshot.comment}</div>
                        )}
                        <div style={{ fontSize: 12, color: '#999' }}>
                          创建时间: {new Date(snapshot.timestamp).toLocaleString()}
                        </div>
                      </>
                    }
                  />
                </List.Item>
              )}
            />
          </TabPane>
        </Tabs>
      </Modal>
    );
  };

  // 执行任务
  const runTask = () => {
    if (!storeValidateYaml(code)) {
      message.error('YAML格式错误，请修正后再运行');
      return;
    }
    
    // 提交任务
    const taskManager = TaskManager.getInstance();
    taskManager.submitTask({
      config: code,
      type: 'train'
    })
    .then(taskId => {
      setTaskId(taskId);
      setIsRunning(true);
      message.info('任务已提交');
    })
    .catch(error => {
      message.error('提交任务失败');
      console.error(error);
    });
  };
  
  // 取消任务
  const cancelTask = () => {
    if (taskId) {
      const taskManager = TaskManager.getInstance();
      taskManager.cancelTask(taskId);
      setIsRunning(false);
      message.info('任务已取消');
    }
  };

  return (
    <div>
      <Card>
        <Row gutter={16}>
          <Col span={24} style={{ marginBottom: 16 }}>
            <Space>
              <Input 
                placeholder="配置名称" 
                value={configName}
                onChange={e => setConfigName(e.target.value)}
                style={{ width: 200 }}
              />
              <Button 
                type="primary" 
                icon={<SaveOutlined />} 
                onClick={() => {
                  if (!storeValidateYaml(code)) {
                    message.error('YAML格式错误，请修正后再保存');
                    return;
                  }
                  
                  if (createVersionSnapshot()) {
                    message.success('配置已保存');
                  }
                }}
              >
                保存
              </Button>
              <Button 
                icon={<PlayCircleOutlined />}
                onClick={runTask}
                disabled={isRunning}
                loading={isRunning}
              >
                {isRunning ? '执行中' : '立即运行'}
              </Button>
              {isRunning && (
                <Button
                  icon={<StopOutlined />}
                  onClick={cancelTask}
                  danger
                >
                  取消任务
                </Button>
              )}
              <Select 
                style={{ width: 200 }} 
                placeholder="选择模板"
                value={selectedTemplate}
                onChange={(value: string) => {
                  setSelectedTemplate(value);
                  setCode(TEMPLATES[value]);
                  storeValidateYaml(TEMPLATES[value]);
                }}
              >
                {Object.keys(TEMPLATES).map(key => (
                  <Select.Option key={key} value={key}>
                    {key}
                  </Select.Option>
                ))}
              </Select>
              <Tooltip title="查看模板帮助">
                <Button 
                  icon={<QuestionCircleOutlined />} 
                  onClick={() => setShowTemplateHelp(true)}
                />
              </Tooltip>
            </Space>
            
            <Space style={{ float: 'right' }}>
              <Button
                icon={<SettingOutlined />}
                onClick={openParameterTuning}
              >
                参数调优
              </Button>
              <Button
                icon={<FileTextOutlined />}
                onClick={() => setTemplateManagerVisible(true)}
              >
                模板管理
              </Button>
              <Button
                icon={<HistoryOutlined />}
                onClick={() => setVersionManagerVisible(true)}
              >
                版本管理
              </Button>
            </Space>
            
            <div style={{ float: 'right', marginRight: 16 }}>
              {isRunning && (
                <div style={{ display: 'inline-block', marginRight: 16 }}>
                  <Progress type="circle" percent={taskProgress} width={32} />
                </div>
              )}
              <Tooltip title="高级验证已启用">
                <Tag 
                  color="green"
                  style={{ cursor: 'pointer' }}
                >
                  高级验证: 开启
                </Tag>
              </Tooltip>
            </div>
          </Col>
          
          <Col span={24}>
            <Tabs activeKey={activeTab} onChange={setActiveTab}>
              <TabPane tab="编辑器" key="editor">
                <MonacoEditor
                  height="600px"
                  language="yaml"
                  theme="vs-dark"
                  value={code}
                  onChange={(value: string | undefined) => {
                    if (value) {
                      setCode(value);
                      storeValidateYaml(value);
                    }
                  }}
                  beforeMount={handleEditorWillMount}
                  onMount={handleEditorDidMount}
                  options={{
                    minimap: { enabled: true },
                    lineNumbers: 'on',
                    scrollBeyondLastLine: false,
                    automaticLayout: true
                  }}
                />
                
                {!isValidYaml && yamlError && (
                  <div style={{ color: 'red', marginTop: 8 }}>
                    错误: {yamlError}
                  </div>
                )}
                {errors.length > 0 && (
                  <div style={{ marginTop: 8 }}>
                    {errors.map((error, index) => (
                      <Alert
                        key={index}
                        message={error.message}
                        type={error.severity === 'error' ? 'error' : error.severity === 'warning' ? 'warning' : 'info'}
                        showIcon
                        style={{ marginBottom: 4 }}
                      />
                    ))}
                  </div>
                )}
              </TabPane>
              <TabPane tab="历史版本" key="history">
                {snapshots.length > 0 ? (
                  <div style={{ maxHeight: '600px', overflow: 'auto' }}>
                    {snapshots.map((snapshot: ConfigSnapshot) => (
                      <Card 
                        key={snapshot.id}
                        size="small" 
                        style={{ marginBottom: 8 }}
                        actions={[
                          <Tooltip title="加载此版本" key="load">
                            <Button 
                              type="text" 
                              icon={<FileTextOutlined />} 
                              onClick={() => handleLoadVersionSnapshot(snapshot.id)}
                            />
                          </Tooltip>,
                          <Tooltip title="复制" key="copy">
                            <Button 
                              type="text" 
                              icon={<CopyOutlined />} 
                              onClick={() => {
                                navigator.clipboard.writeText(snapshot.content).then(() => {
                                  message.success('已复制到剪贴板');
                                }).catch((err) => {
                                  console.error('复制到剪贴板失败:', err);
                                  message.error('复制失败，请手动选择并复制内容');
                                });
                              }}
                            />
                          </Tooltip>
                        ]}
                      >
                        <div>
                          <strong>{snapshot.name}</strong>
                          {snapshot.comment && (
                            <div style={{ fontSize: 13 }}>{snapshot.comment}</div>
                          )}
                          <div style={{ fontSize: 12, color: '#888' }}>
                            保存时间: {new Date(snapshot.timestamp).toLocaleString()}
                          </div>
                        </div>
                      </Card>
                    ))}
                  </div>
                ) : (
                  <div style={{ textAlign: 'center', padding: 24 }}>
                    <HistoryOutlined style={{ fontSize: 32, color: '#ccc' }} />
                    <p>暂无历史版本记录</p>
                  </div>
                )}
              </TabPane>
            </Tabs>
          </Col>
        </Row>
      </Card>
      
      <Modal
        title="模板预览"
        width={800}
        open={showTemplateHelp}
        onCancel={() => setShowTemplateHelp(false)}
        footer={null}
      >
        <Tabs defaultActiveKey="basic">
          {Object.keys(TEMPLATES).map(key => (
            <TabPane tab={key} key={key}>
              <MonacoEditor
                height="400px"
                language="yaml"
                value={TEMPLATES[key]}
                options={{
                  readOnly: true,
                  minimap: { enabled: false },
                  scrollBeyondLastLine: false
                }}
              />
            </TabPane>
          ))}
        </Tabs>
      </Modal>
      
      <Modal
        title="参数调优"
        open={isParameterTuningVisible}
        onCancel={() => setParameterTuningVisible(false)}
        footer={null}
      >
        {renderParameterTuningForm()}
      </Modal>
      
      {renderTemplateManager()}
      {renderVersionManager()}
    </div>
  );
};

export default ConfigEditor;
