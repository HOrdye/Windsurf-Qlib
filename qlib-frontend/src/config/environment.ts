/**
 * 环境配置文件
 * 提供不同环境（开发、测试、生产）的配置
 */

// 环境类型
export type Environment = 'development' | 'test' | 'production';

// 当前环境
export const currentEnvironment: Environment = 
  (process.env.REACT_APP_ENV as Environment) || 'development';

// WebSocket 配置
interface WebSocketEnvConfig {
  url: string;
  heartbeatInterval: number; // 毫秒
  heartbeatTimeout: number;  // 毫秒
  reconnectMaxAttempts: number;
  reconnectBaseDelay: number; // 毫秒
  reconnectMaxDelay: number;  // 毫秒
  inactivityTimeout: number;  // 毫秒，长时间未活动超时时间
}

// API 配置
interface ApiEnvConfig {
  baseUrl: string;
  timeout: number; // 毫秒
}

// 环境配置接口
interface EnvConfig {
  websocket: WebSocketEnvConfig;
  api: ApiEnvConfig;
  debug: boolean;
}

// 环境配置映射
const envConfigs: Record<Environment, EnvConfig> = {
  // 开发环境配置
  development: {
    websocket: {
      url: 'ws://localhost:8080/ws',
      heartbeatInterval: 30000, // 30秒
      heartbeatTimeout: 5000,   // 5秒
      reconnectMaxAttempts: 10,
      reconnectBaseDelay: 1000,  // 1秒
      reconnectMaxDelay: 30000,  // 30秒
      inactivityTimeout: 300000, // 5分钟
    },
    api: {
      baseUrl: 'http://localhost:8080/api',
      timeout: 10000, // 10秒
    },
    debug: true,
  },
  
  // 测试环境配置
  test: {
    websocket: {
      url: 'ws://test-server:8081/ws',
      heartbeatInterval: 30000,
      heartbeatTimeout: 5000,
      reconnectMaxAttempts: 10,
      reconnectBaseDelay: 1000,
      reconnectMaxDelay: 30000,
      inactivityTimeout: 300000, // 5分钟
    },
    api: {
      baseUrl: 'http://test-server:8081/api',
      timeout: 10000,
    },
    debug: true,
  },
  
  // 生产环境配置
  production: {
    websocket: {
      url: 'ws://qlib-server:8080/ws',
      heartbeatInterval: 60000, // 1分钟
      heartbeatTimeout: 10000,  // 10秒
      reconnectMaxAttempts: 5,
      reconnectBaseDelay: 2000,  // 2秒
      reconnectMaxDelay: 60000,  // 1分钟
      inactivityTimeout: 900000, // 15分钟
    },
    api: {
      baseUrl: 'http://qlib-server:8080/api',
      timeout: 30000, // 30秒
    },
    debug: false,
  },
};

// 获取当前环境配置
export const config = envConfigs[currentEnvironment];

// 允许通过环境变量覆盖配置
if (process.env.REACT_APP_WS_URL) {
  config.websocket.url = process.env.REACT_APP_WS_URL;
}

if (process.env.REACT_APP_API_URL) {
  config.api.baseUrl = process.env.REACT_APP_API_URL;
}

// 导出配置
export default config;
