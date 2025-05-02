import { create } from 'zustand';
import { persist } from 'zustand/middleware';

// 应用设置接口
interface AppSettings {
  general: {
    username: string;
    password: string;
    language: 'zh_CN' | 'en_US';
    theme: 'light' | 'dark';
    autoSave: boolean;
    autoSync: boolean;
  };
  server: {
    apiUrl: string;
    wsUrl: string;
    useHttps: boolean;
    timeout: number;
  };
  data: {
    defaultProvider: 'local' | 'remote';
    cacheEnabled: boolean;
    cachePath: string;
    preloadDatasets: string[];
    autoCleanCache: boolean;
    cleanCacheInterval: number;
  };
}

// 设置状态接口
interface SettingsState extends AppSettings {
  // 更新整个设置
  updateSettings: (settings: AppSettings) => void;
  
  // 更新部分设置
  updateGeneralSettings: (general: Partial<AppSettings['general']>) => void;
  updateServerSettings: (server: Partial<AppSettings['server']>) => void;
  updateDataSettings: (data: Partial<AppSettings['data']>) => void;
  
  // 重置为默认设置
  resetSettings: () => void;
}

// 默认设置
const defaultSettings: AppSettings = {
  general: {
    username: '',
    password: '',
    language: 'zh_CN',
    theme: 'light',
    autoSave: true,
    autoSync: false
  },
  server: {
    apiUrl: 'http://127.0.0.1:8080',
    wsUrl: 'ws://127.0.0.1:8080/ws',
    useHttps: false,
    timeout: 30000
  },
  data: {
    defaultProvider: 'local',
    cacheEnabled: true,
    cachePath: '~/.qlib/cache',
    preloadDatasets: ['csi300'],
    autoCleanCache: true,
    cleanCacheInterval: 7
  }
};

// 创建设置状态管理
export const useSettingsStore = create(
  persist(
    (set) => ({
      ...defaultSettings,
      
      updateSettings: (settings: AppSettings) => {
        set({ ...settings });
      },
      
      updateGeneralSettings: (general: Partial<AppSettings['general']>) => {
        set((state) => ({
          general: {
            ...state.general,
            ...general
          }
        }));
      },
      
      updateServerSettings: (server: Partial<AppSettings['server']>) => {
        set((state) => ({
          server: {
            ...state.server,
            ...server
          }
        }));
      },
      
      updateDataSettings: (data: Partial<AppSettings['data']>) => {
        set((state) => ({
          data: {
            ...state.data,
            ...data
          }
        }));
      },
      
      resetSettings: () => {
        set(defaultSettings);
      }
    }),
    {
      name: 'qlib-settings-storage',
      // 排除敏感信息不持久化到localStorage
      partialize: (state) => ({
        general: {
          ...state.general,
          // 不存储密码
          password: ''
        },
        server: state.server,
        data: state.data
      })
    }
  )
);
