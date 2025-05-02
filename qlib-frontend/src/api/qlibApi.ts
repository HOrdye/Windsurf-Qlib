import axios, { AxiosInstance, AxiosRequestConfig } from 'axios';
import mockApiResponses from '../mocks/mockApiServer';

/**
 * Qlib API接口类
 * 负责与Qlib后端服务通信
 */
class QlibApi {
  private client: AxiosInstance;
  private baseUrl: string = 'http://localhost:8080';

  constructor() {
    this.client = axios.create({
      baseURL: this.baseUrl,
      timeout: 30000,
      headers: {
        'Content-Type': 'application/json'
      },
      withCredentials: false
    });

    // 环境变量，控制是否使用模拟API
    const USE_MOCK_API = process.env.NODE_ENV === 'development' && false; // 设置为true启用模拟API

    if (USE_MOCK_API) {
      // 使用模拟API响应
      this.client.interceptors.request.use((config) => {
        const mockResponse = mockApiResponses[config.url];
        if (mockResponse) {
          return Promise.resolve({
            data: mockResponse,
            status: 200,
            statusText: 'OK',
            headers: {},
            config: config,
            request: {}
          });
        }
        return config;
      });
    } else {
      // 请求拦截器 - 添加认证信息
      this.client.interceptors.request.use(
        (config) => {
          const username = localStorage.getItem('qlib_username');
          const password = localStorage.getItem('qlib_password');
          
          if (username && password) {
            const token = btoa(`${username}:${password}`);
            config.headers.Authorization = `Basic ${token}`;
          }
          
          return config;
        },
        (error) => {
          return Promise.reject(error);
        }
      );
    }

    // 响应拦截器 - 统一错误处理
    this.client.interceptors.response.use(
      (response) => {
        return response;
      },
      (error) => {
        console.error('API请求错误:', error);
        return Promise.reject(error);
      }
    );
  }

  /**
   * 设置API基础URL
   * @param url 基础URL
   */
  public setBaseUrl(url: string): void {
    this.baseUrl = url;
    this.client.defaults.baseURL = url;
  }

  /**
   * 设置请求超时时间
   * @param timeout 超时时间(毫秒)
   */
  public setTimeout(timeout: number): void {
    this.client.defaults.timeout = timeout;
  }

  /**
   * 初始化Qlib
   * @param config Qlib初始化配置
   */
  public async initQlib(config: any): Promise<any> {
    return this.client.post('/api/qlib/init', config);
  }

  /**
   * 获取可用数据集列表
   */
  public async getDatasets(): Promise<any> {
    return this.client.get('/api/datasets');
  }

  /**
   * 上传配置文件
   * @param config 配置内容
   * @param name 配置名称
   */
  public async uploadConfig(config: string, name: string): Promise<any> {
    return this.client.post('/api/configs', { content: config, name });
  }

  /**
   * 获取配置文件列表
   */
  public async getConfigs(): Promise<any> {
    return this.client.get('/api/configs');
  }

  /**
   * 获取配置文件详情
   * @param id 配置ID
   */
  public async getConfig(id: string): Promise<any> {
    return this.client.get(`/api/configs/${id}`);
  }

  /**
   * 运行任务
   * @param configId 配置ID
   * @param taskType 任务类型 (training, backtest, data_init)
   */
  public async runTask(configId: string, taskType: string): Promise<any> {
    return this.client.post('/api/tasks', { config_id: configId, type: taskType });
  }

  /**
   * 运行自定义YAML任务
   * @param yamlContent YAML配置内容
   * @param taskName 任务名称
   * @param taskType 任务类型
   */
  public async runYamlTask(yamlContent: string, taskName: string, taskType: string): Promise<any> {
    return this.client.post('/api/tasks/yaml', { 
      content: yamlContent,
      name: taskName,
      type: taskType
    });
  }

  /**
   * 获取任务列表
   */
  public async getTasks(): Promise<any> {
    return this.client.get('/api/tasks');
  }

  /**
   * 获取任务详情
   * @param taskId 任务ID
   */
  public async getTask(taskId: string): Promise<any> {
    return this.client.get(`/api/tasks/${taskId}`);
  }

  /**
   * 获取任务日志
   * @param taskId 任务ID
   */
  public async getTaskLogs(taskId: string): Promise<any> {
    return this.client.get(`/api/tasks/${taskId}/logs`);
  }

  /**
   * 停止任务
   * @param taskId 任务ID
   */
  public async stopTask(taskId: string): Promise<any> {
    return this.client.post(`/api/tasks/${taskId}/stop`);
  }

  /**
   * 获取回测结果
   * @param taskId 任务ID
   */
  public async getBacktestResults(taskId: string): Promise<any> {
    return this.client.get(`/api/tasks/${taskId}/backtest`);
  }

  /**
   * 获取回测指标
   * @param taskId 任务ID
   */
  public async getBacktestMetrics(taskId: string): Promise<any> {
    return this.client.get(`/api/tasks/${taskId}/metrics`);
  }

  /**
   * 导出回测结果为CSV
   * @param taskId 任务ID
   */
  public async exportBacktestToCsv(taskId: string): Promise<any> {
    return this.client.get(`/api/tasks/${taskId}/export/csv`, {
      responseType: 'blob'
    });
  }

  /**
   * 上传文档用于Alpha因子生成
   * @param file 文档文件
   * @param documentType 文档类型 (pdf, docx, webpage)
   */
  public async uploadDocument(file: File, documentType: string): Promise<any> {
    if (process.env.NODE_ENV === 'development' && false) {
      return Promise.resolve(mockApiResponses.uploadDocument(file, documentType));
    }
    
    const formData = new FormData();
    formData.append('file', file);
    formData.append('type', documentType);
    
    return this.client.post('/api/alpha/documents/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    });
  }

  /**
   * 从URL解析网页文档
   * @param url 网页URL
   */
  public async parseWebDocument(url: string): Promise<any> {
    if (process.env.NODE_ENV === 'development' && false) {
      return Promise.resolve(mockApiResponses.parseWebDocument(url));
    }
    
    return this.client.post('/api/alpha/documents/parse-url', { url });
  }

  /**
   * 从文档提取Alpha因子信号
   * @param documentId 文档ID
   * @param extractorType 提取器类型 (rule, llm, ensemble)
   */
  public async extractAlphaSignals(documentId: string, extractorType: string): Promise<any> {
    if (process.env.NODE_ENV === 'development' && false) {
      return Promise.resolve(mockApiResponses.extractAlphaSignals(documentId, extractorType));
    }
    
    return this.client.post('/api/alpha/extract', { 
      document_id: documentId,
      extractor_type: extractorType
    });
  }

  /**
   * 验证Alpha因子信号
   * @param signalIds Alpha因子信号ID列表
   * @param validatorType 验证器类型 (basic, backtest)
   */
  public async validateAlphaSignals(signalIds: string[], validatorType: string): Promise<any> {
    if (process.env.NODE_ENV === 'development' && false) {
      return Promise.resolve(mockApiResponses.validateAlphaSignals(signalIds, validatorType));
    }
    
    return this.client.post('/api/alpha/validate', {
      signal_ids: signalIds,
      validator_type: validatorType
    });
  }

  /**
   * 获取所有Alpha因子信号
   */
  public async getAlphaSignals(): Promise<any> {
    if (process.env.NODE_ENV === 'development' && false) {
      return Promise.resolve({
        status: 200,
        data: {
          signals: mockApiResponses.extractAlphaSignals('mock-doc', 'ensemble').data.signals
        }
      });
    }
    
    return this.client.get('/api/alpha/signals');
  }

  /**
   * 获取特定Alpha因子信号详情
   * @param signalId 信号ID
   */
  public async getAlphaSignalDetails(signalId: string): Promise<any> {
    if (process.env.NODE_ENV === 'development' && false) {
      const allSignals = mockApiResponses.extractAlphaSignals('mock-doc', 'ensemble').data.signals;
      const signal = allSignals.find((s: any) => s.id === signalId) || allSignals[0];
      
      return Promise.resolve({
        status: 200,
        data: signal
      });
    }
    
    return this.client.get(`/api/alpha/signals/${signalId}`);
  }

  /**
   * 导出Alpha因子信号为CSV
   * @param signalIds 信号ID列表
   */
  public async exportAlphaSignalsToCsv(signalIds: string[]): Promise<any> {
    if (process.env.NODE_ENV === 'development' && false) {
      return Promise.resolve(mockApiResponses.exportAlphaSignalsToCsv(signalIds));
    }
    
    return this.client.post('/api/alpha/signals/export/csv', {
      signal_ids: signalIds
    }, {
      responseType: 'blob'
    });
  }

  /**
   * 发送自定义请求
   * @param url 请求URL
   * @param method 请求方法
   * @param data 请求数据
   * @param config 请求配置
   */
  public request(url: string, method: string, data?: any, config?: AxiosRequestConfig): Promise<any> {
    const requestConfig: AxiosRequestConfig = {
      ...config,
      url,
      method,
      data,
      baseURL: this.baseUrl
    };
    
    // 直接使用axios发起请求，而不是client.request
    return axios(requestConfig);
  }
}

// 导出单例实例
export const qlibApi = new QlibApi();
export default qlibApi;
