/**
 * Jest 测试环境设置文件
 * 用于配置测试环境和提供浏览器 API 的模拟实现
 */

import '@testing-library/jest-dom';

// 模拟 window.matchMedia
window.matchMedia = window.matchMedia || function(query) {
  return {
    matches: false,
    media: query,
    onchange: null,
    addListener: function(listener) {
      this.addEventListener('change', listener);
    },
    removeListener: function(listener) {
      this.removeEventListener('change', listener);
    },
    addEventListener: jest.fn(),
    removeEventListener: jest.fn(),
    dispatchEvent: jest.fn(),
  };
};

// 模拟 ResizeObserver
class ResizeObserverMock {
  observe = jest.fn();
  unobserve = jest.fn();
  disconnect = jest.fn();
}

global.ResizeObserver = ResizeObserverMock;

// 模拟 IntersectionObserver
const mockIntersectionObserver = jest.fn().mockImplementation((callback) => {
  return {
    root: null,
    rootMargin: '',
    thresholds: [0],
    observe: jest.fn(),
    unobserve: jest.fn(),
    disconnect: jest.fn(),
    takeRecords: jest.fn().mockReturnValue([]),
    // 手动触发回调的辅助方法
    triggerCallback: (entries: IntersectionObserverEntry[]) => {
      callback(entries, {
        root: null,
        rootMargin: '',
        thresholds: [0],
        observe: jest.fn(),
        unobserve: jest.fn(),
        disconnect: jest.fn(),
        takeRecords: jest.fn().mockReturnValue([])
      });
    }
  };
});

global.IntersectionObserver = mockIntersectionObserver as unknown as typeof IntersectionObserver;

// 模拟 HTMLElement.prototype.scrollIntoView
if (typeof HTMLElement.prototype.scrollIntoView !== 'function') {
  HTMLElement.prototype.scrollIntoView = jest.fn();
}

// 模拟 localStorage
const localStorageMock = (function() {
  let store: Record<string, string> = {};
  
  return {
    getItem: function(key: string) {
      return store[key] || null;
    },
    setItem: function(key: string, value: string) {
      store[key] = value.toString();
    },
    removeItem: function(key: string) {
      delete store[key];
    },
    clear: function() {
      store = {};
    }
  };
})();

Object.defineProperty(window, 'localStorage', {
  value: localStorageMock
});

// 模拟 sessionStorage
Object.defineProperty(window, 'sessionStorage', {
  value: localStorageMock
});

// 模拟 indexedDB
const indexedDBMock = {
  open: jest.fn().mockReturnValue({
    onupgradeneeded: null,
    onsuccess: null,
    onerror: null,
    result: {
      createObjectStore: jest.fn(),
      transaction: jest.fn().mockReturnValue({
        objectStore: jest.fn().mockReturnValue({
          put: jest.fn(),
          get: jest.fn(),
          getAll: jest.fn(),
          delete: jest.fn(),
          clear: jest.fn(),
          index: jest.fn().mockReturnValue({
            get: jest.fn(),
            getAll: jest.fn()
          })
        }),
        oncomplete: null,
        onerror: null
      })
    }
  })
};

Object.defineProperty(window, 'indexedDB', {
  value: indexedDBMock
});

// 模拟 performance API
if (!window.performance) {
  Object.defineProperty(window, 'performance', {
    value: {
      now: jest.fn().mockReturnValue(Date.now()),
      mark: jest.fn(),
      measure: jest.fn(),
      getEntriesByName: jest.fn().mockReturnValue([]),
      getEntriesByType: jest.fn().mockReturnValue([]),
      clearMarks: jest.fn(),
      clearMeasures: jest.fn()
    }
  });
}
