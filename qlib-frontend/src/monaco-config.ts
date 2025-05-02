/**
 * Monaco Editor 配置文件
 * 用于配置 Monaco Editor 的 worker 路径和其他设置
 */

import * as monaco from 'monaco-editor';

// 配置 Monaco Editor 的 worker 路径
export function configureMonacoWorkers() {
  try {
    // @ts-ignore - 忽略类型错误，因为 window.MonacoEnvironment 在 TypeScript 类型定义中不存在
    window.MonacoEnvironment = {
      getWorkerUrl: function (_moduleId: string, label: string) {
        // 使用公共路径下的 worker 文件
        const workerPath = '/monaco-editor-workers';
        
        if (label === 'json') {
          return `${workerPath}/json.worker.js`;
        }
        if (label === 'css' || label === 'scss' || label === 'less') {
          return `${workerPath}/css.worker.js`;
        }
        if (label === 'html' || label === 'handlebars' || label === 'razor') {
          return `${workerPath}/html.worker.js`;
        }
        if (label === 'typescript' || label === 'javascript') {
          return `${workerPath}/ts.worker.js`;
        }
        return `${workerPath}/editor.worker.js`;
      }
    };
    console.log('[Monaco] Workers configured successfully');
  } catch (error) {
    console.error('[Monaco] Failed to configure workers:', error);
  }
}

// 自定义 YAML 语法高亮规则
const yamlTokensProvider = {
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
};

// 配置 Monaco Editor 的 YAML 支持
export function configureMonaco() {
  // 配置 worker
  configureMonacoWorkers();
  
  try {
    // 注册 YAML 语言
    if (monaco && monaco.languages) {
      // 使用 any 类型绕过类型检查
      const languages = monaco.languages as any;
      
      // 注册 YAML 语言
      languages.register({ id: 'yaml', extensions: ['.yml', '.yaml'] });
      
      // 配置 YAML 语法高亮
      languages.setMonarchTokensProvider('yaml', yamlTokensProvider);
      
      console.log('[Monaco] YAML language registered successfully');
    } else {
      console.warn('[Monaco] Languages API not available');
    }
  } catch (error) {
    console.error('[Monaco] Failed to register YAML language:', error);
  }
  
  console.log('[Monaco] Configuration completed');
}
