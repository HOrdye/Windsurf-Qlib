/**
 * 缓存服务
 * 提供IndexedDB和LocalStorage的统一接口
 */

// IndexedDB数据库名称和版本
const DB_NAME = 'qlib-cache';
const DB_VERSION = 1;

// 存储对象名称
const STORES = {
  CONFIG_SNAPSHOTS: 'configSnapshots',
  CONFIG_TEMPLATES: 'configTemplates',
  DATASET_METADATA: 'datasetMetadata',
  TASK_RESULTS: 'taskResults'
};

// 缓存键前缀
const CACHE_KEYS = {
  RECENT_CONFIGS: 'recentConfigs',
  FREQUENT_DATASETS: 'frequentDatasets',
  UI_PREFERENCES: 'uiPreferences',
  LAST_SESSION: 'lastSession'
};

/**
 * 打开IndexedDB数据库连接
 */
const openDatabase = (): Promise<IDBDatabase> => {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(DB_NAME, DB_VERSION);
    
    request.onerror = (event) => {
      console.error('IndexedDB打开失败:', event);
      reject(new Error('无法打开IndexedDB数据库'));
    };
    
    request.onsuccess = (event) => {
      const db = (event.target as IDBOpenDBRequest).result;
      resolve(db);
    };
    
    request.onupgradeneeded = (event) => {
      const db = (event.target as IDBOpenDBRequest).result;
      
      // 创建配置快照存储
      if (!db.objectStoreNames.contains(STORES.CONFIG_SNAPSHOTS)) {
        const store = db.createObjectStore(STORES.CONFIG_SNAPSHOTS, { keyPath: 'id' });
        store.createIndex('timestamp', 'timestamp', { unique: false });
        store.createIndex('name', 'name', { unique: false });
      }
      
      // 创建配置模板存储
      if (!db.objectStoreNames.contains(STORES.CONFIG_TEMPLATES)) {
        const store = db.createObjectStore(STORES.CONFIG_TEMPLATES, { keyPath: 'id' });
        store.createIndex('name', 'name', { unique: false });
      }
      
      // 创建数据集元数据存储
      if (!db.objectStoreNames.contains(STORES.DATASET_METADATA)) {
        const store = db.createObjectStore(STORES.DATASET_METADATA, { keyPath: 'id' });
        store.createIndex('name', 'name', { unique: false });
        store.createIndex('lastAccessed', 'lastAccessed', { unique: false });
      }
      
      // 创建任务结果缓存存储
      if (!db.objectStoreNames.contains(STORES.TASK_RESULTS)) {
        const store = db.createObjectStore(STORES.TASK_RESULTS, { keyPath: 'taskId' });
        store.createIndex('timestamp', 'timestamp', { unique: false });
        store.createIndex('type', 'type', { unique: false });
      }
    };
  });
};

/**
 * IndexedDB操作类
 * 提供对IndexedDB的增删改查操作
 */
class IndexedDBService {
  /**
   * 保存数据到指定存储
   * @param storeName 存储名称
   * @param data 要保存的数据
   */
  static async save<T>(storeName: string, data: T): Promise<T> {
    try {
      const db = await openDatabase();
      return new Promise((resolve, reject) => {
        const transaction = db.transaction(storeName, 'readwrite');
        const store = transaction.objectStore(storeName);
        const request = store.put(data);
        
        request.onsuccess = () => {
          resolve(data);
        };
        
        request.onerror = (event) => {
          console.error(`保存到${storeName}失败:`, event);
          reject(new Error(`保存到${storeName}失败`));
        };
        
        transaction.oncomplete = () => {
          db.close();
        };
      });
    } catch (error) {
      console.error('IndexedDB保存操作失败:', error);
      throw error;
    }
  }
  
  /**
   * 获取指定存储中的所有数据
   * @param storeName 存储名称
   */
  static async getAll<T>(storeName: string): Promise<T[]> {
    try {
      const db = await openDatabase();
      return new Promise((resolve, reject) => {
        const transaction = db.transaction(storeName, 'readonly');
        const store = transaction.objectStore(storeName);
        const request = store.getAll();
        
        request.onsuccess = (event) => {
          resolve((event.target as IDBRequest).result);
        };
        
        request.onerror = (event) => {
          console.error(`从${storeName}获取所有数据失败:`, event);
          reject(new Error(`从${storeName}获取所有数据失败`));
        };
        
        transaction.oncomplete = () => {
          db.close();
        };
      });
    } catch (error) {
      console.error('IndexedDB获取操作失败:', error);
      throw error;
    }
  }
  
  /**
   * 根据ID获取数据
   * @param storeName 存储名称
   * @param id 数据ID
   */
  static async getById<T>(storeName: string, id: string): Promise<T | undefined> {
    try {
      const db = await openDatabase();
      return new Promise((resolve, reject) => {
        const transaction = db.transaction(storeName, 'readonly');
        const store = transaction.objectStore(storeName);
        const request = store.get(id);
        
        request.onsuccess = (event) => {
          resolve((event.target as IDBRequest).result);
        };
        
        request.onerror = (event) => {
          console.error(`从${storeName}获取ID=${id}的数据失败:`, event);
          reject(new Error(`从${storeName}获取数据失败`));
        };
        
        transaction.oncomplete = () => {
          db.close();
        };
      });
    } catch (error) {
      console.error('IndexedDB获取操作失败:', error);
      throw error;
    }
  }
  
  /**
   * 根据索引获取数据
   * @param storeName 存储名称
   * @param indexName 索引名称
   * @param value 索引值
   */
  static async getByIndex<T>(storeName: string, indexName: string, value: any): Promise<T[]> {
    try {
      const db = await openDatabase();
      return new Promise((resolve, reject) => {
        const transaction = db.transaction(storeName, 'readonly');
        const store = transaction.objectStore(storeName);
        const index = store.index(indexName);
        const request = index.getAll(value);
        
        request.onsuccess = (event) => {
          resolve((event.target as IDBRequest).result);
        };
        
        request.onerror = (event) => {
          console.error(`从${storeName}通过索引${indexName}=${value}获取数据失败:`, event);
          reject(new Error(`通过索引获取数据失败`));
        };
        
        transaction.oncomplete = () => {
          db.close();
        };
      });
    } catch (error) {
      console.error('IndexedDB索引查询失败:', error);
      throw error;
    }
  }
  
  /**
   * 删除数据
   * @param storeName 存储名称
   * @param id 数据ID
   */
  static async delete(storeName: string, id: string): Promise<void> {
    try {
      const db = await openDatabase();
      return new Promise((resolve, reject) => {
        const transaction = db.transaction(storeName, 'readwrite');
        const store = transaction.objectStore(storeName);
        const request = store.delete(id);
        
        request.onsuccess = () => {
          resolve();
        };
        
        request.onerror = (event) => {
          console.error(`从${storeName}删除ID=${id}的数据失败:`, event);
          reject(new Error(`删除数据失败`));
        };
        
        transaction.oncomplete = () => {
          db.close();
        };
      });
    } catch (error) {
      console.error('IndexedDB删除操作失败:', error);
      throw error;
    }
  }
  
  /**
   * 清空存储
   * @param storeName 存储名称
   */
  static async clear(storeName: string): Promise<void> {
    try {
      const db = await openDatabase();
      return new Promise((resolve, reject) => {
        const transaction = db.transaction(storeName, 'readwrite');
        const store = transaction.objectStore(storeName);
        const request = store.clear();
        
        request.onsuccess = () => {
          resolve();
        };
        
        request.onerror = (event) => {
          console.error(`清空${storeName}失败:`, event);
          reject(new Error(`清空存储失败`));
        };
        
        transaction.oncomplete = () => {
          db.close();
        };
      });
    } catch (error) {
      console.error('IndexedDB清空操作失败:', error);
      throw error;
    }
  }
}

/**
 * LocalStorage操作类
 * 提供对LocalStorage的增删改查操作
 */
class LocalStorageService {
  /**
   * 保存数据到LocalStorage
   * @param key 键
   * @param data 数据
   */
  static save<T>(key: string, data: T): void {
    try {
      localStorage.setItem(key, JSON.stringify(data));
    } catch (error) {
      console.error(`保存到LocalStorage失败, key=${key}:`, error);
      throw error;
    }
  }
  
  /**
   * 从LocalStorage获取数据
   * @param key 键
   * @param defaultValue 默认值
   */
  static get<T>(key: string, defaultValue?: T): T | undefined {
    try {
      const data = localStorage.getItem(key);
      return data ? JSON.parse(data) : defaultValue;
    } catch (error) {
      console.error(`从LocalStorage获取数据失败, key=${key}:`, error);
      return defaultValue;
    }
  }
  
  /**
   * 从LocalStorage删除数据
   * @param key 键
   */
  static delete(key: string): void {
    try {
      localStorage.removeItem(key);
    } catch (error) {
      console.error(`从LocalStorage删除数据失败, key=${key}:`, error);
      throw error;
    }
  }
  
  /**
   * 清空LocalStorage
   */
  static clear(): void {
    try {
      localStorage.clear();
    } catch (error) {
      console.error('清空LocalStorage失败:', error);
      throw error;
    }
  }
}

/**
 * 缓存服务
 * 统一提供IndexedDB和LocalStorage的操作接口
 */
class CacheService {
  // 将IndexedDBService作为静态属性
  static IndexedDBService = IndexedDBService;
  // 将LocalStorageService作为静态属性
  static LocalStorageService = LocalStorageService;

  /**
   * 保存配置快照
   * @param snapshot 配置快照
   */
  static async saveConfigSnapshot(snapshot: any): Promise<any> {
    return IndexedDBService.save(STORES.CONFIG_SNAPSHOTS, {
      ...snapshot,
      timestamp: snapshot.timestamp || Date.now()
    });
  }
  
  /**
   * 获取所有配置快照
   */
  static async getAllConfigSnapshots(): Promise<any[]> {
    return IndexedDBService.getAll(STORES.CONFIG_SNAPSHOTS);
  }
  
  /**
   * 获取指定ID的配置快照
   * @param id 快照ID
   */
  static async getConfigSnapshotById(id: string): Promise<any | undefined> {
    return IndexedDBService.getById(STORES.CONFIG_SNAPSHOTS, id);
  }
  
  /**
   * 删除配置快照
   * @param id 快照ID
   */
  static async deleteConfigSnapshot(id: string): Promise<void> {
    return IndexedDBService.delete(STORES.CONFIG_SNAPSHOTS, id);
  }
  
  /**
   * 保存配置模板
   * @param template 配置模板
   */
  static async saveConfigTemplate(template: any): Promise<any> {
    return IndexedDBService.save(STORES.CONFIG_TEMPLATES, template);
  }
  
  /**
   * 获取所有配置模板
   */
  static async getAllConfigTemplates(): Promise<any[]> {
    return IndexedDBService.getAll(STORES.CONFIG_TEMPLATES);
  }
  
  /**
   * 获取指定ID的配置模板
   * @param id 模板ID
   */
  static async getConfigTemplateById(id: string): Promise<any | undefined> {
    return IndexedDBService.getById(STORES.CONFIG_TEMPLATES, id);
  }
  
  /**
   * 删除配置模板
   * @param id 模板ID
   */
  static async deleteConfigTemplate(id: string): Promise<void> {
    return IndexedDBService.delete(STORES.CONFIG_TEMPLATES, id);
  }
  
  /**
   * 保存数据集元数据
   * @param metadata 数据集元数据
   */
  static async saveDatasetMetadata(metadata: any): Promise<any> {
    return IndexedDBService.save(STORES.DATASET_METADATA, {
      ...metadata,
      lastAccessed: Date.now()
    });
  }
  
  /**
   * 获取所有数据集元数据
   */
  static async getAllDatasetMetadata(): Promise<any[]> {
    return IndexedDBService.getAll(STORES.DATASET_METADATA);
  }
  
  /**
   * 获取最近访问的数据集元数据
   * @param limit 限制数量
   */
  static async getRecentDatasetMetadata(limit: number = 10): Promise<any[]> {
    const allMetadata = await IndexedDBService.getAll<any>(STORES.DATASET_METADATA);
    return allMetadata
      .sort((a, b) => b.lastAccessed - a.lastAccessed)
      .slice(0, limit);
  }
  
  /**
   * 保存任务结果
   * @param taskResult 任务结果
   */
  static async saveTaskResult(taskResult: any): Promise<any> {
    return IndexedDBService.save(STORES.TASK_RESULTS, {
      ...taskResult,
      timestamp: Date.now()
    });
  }
  
  /**
   * 获取任务结果
   * @param taskId 任务ID
   */
  static async getTaskResult(taskId: string): Promise<any | undefined> {
    return IndexedDBService.getById(STORES.TASK_RESULTS, taskId);
  }
  
  /**
   * 获取指定类型的任务结果
   * @param type 任务类型
   */
  static async getTaskResultsByType(type: string): Promise<any[]> {
    return IndexedDBService.getByIndex(STORES.TASK_RESULTS, 'type', type);
  }
  
  /**
   * 删除任务结果
   * @param taskId 任务ID
   */
  static async deleteTaskResult(taskId: string): Promise<void> {
    return IndexedDBService.delete(STORES.TASK_RESULTS, taskId);
  }
  
  /**
   * 保存最近使用的配置列表
   * @param configs 配置列表
   */
  static saveRecentConfigs(configs: any[]): void {
    LocalStorageService.save(CACHE_KEYS.RECENT_CONFIGS, configs);
  }
  
  /**
   * 获取最近使用的配置列表
   */
  static getRecentConfigs(): any[] {
    return LocalStorageService.get<any[]>(CACHE_KEYS.RECENT_CONFIGS, []);
  }
  
  /**
   * 保存常用数据集列表
   * @param datasets 数据集列表
   */
  static saveFrequentDatasets(datasets: any[]): void {
    LocalStorageService.save(CACHE_KEYS.FREQUENT_DATASETS, datasets);
  }
  
  /**
   * 获取常用数据集列表
   */
  static getFrequentDatasets(): any[] {
    return LocalStorageService.get<any[]>(CACHE_KEYS.FREQUENT_DATASETS, []);
  }
  
  /**
   * 保存UI偏好设置
   * @param preferences UI偏好设置
   */
  static saveUIPreferences(preferences: any): void {
    LocalStorageService.save(CACHE_KEYS.UI_PREFERENCES, preferences);
  }
  
  /**
   * 获取UI偏好设置
   */
  static getUIPreferences(): any {
    return LocalStorageService.get(CACHE_KEYS.UI_PREFERENCES, {});
  }
  
  /**
   * 保存会话状态
   * @param sessionState 会话状态
   */
  static saveLastSession(sessionState: any): void {
    LocalStorageService.save(CACHE_KEYS.LAST_SESSION, sessionState);
  }
  
  /**
   * 获取会话状态
   */
  static getLastSession(): any {
    return LocalStorageService.get(CACHE_KEYS.LAST_SESSION, {});
  }
  
  /**
   * 清除所有缓存
   */
  static async clearAll(): Promise<void> {
    // 清除IndexedDB
    await IndexedDBService.clear(STORES.CONFIG_SNAPSHOTS);
    await IndexedDBService.clear(STORES.CONFIG_TEMPLATES);
    await IndexedDBService.clear(STORES.DATASET_METADATA);
    await IndexedDBService.clear(STORES.TASK_RESULTS);
    
    // 清除LocalStorage
    LocalStorageService.clear();
  }
}

export default CacheService;
